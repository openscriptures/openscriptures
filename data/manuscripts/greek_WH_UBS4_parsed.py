#!/usr/bin/env python
# encoding: utf-8

msID = 2
varMsID = 3

import sys, os, re, unicodedata, difflib, zipfile, StringIO
from datetime import date
from django.core.management import setup_environ
from django.utils.encoding import smart_str, smart_unicode
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../')) #There's probably a better way of doing this
from openscriptures import settings
setup_environ(settings)
from openscriptures.data.unbound_bible import UNBOUND_CODE_TO_OSIS_CODE # Why does this have to be explicit?
from openscriptures.data import import_helpers
from openscriptures.core.models import *

# Abort if MS has already been added (or --force not supplied)
import_helpers.abort_if_imported(msID)

# Download the source file
source_url = "http://www.unboundbible.org/downloads/bibles/greek_WH_UBS4_parsed.zip"
import_helpers.download_resource(source_url)

# Delete existing works and their contents
import_helpers.delete_work(msID, varMsID)

msWork = Work(
    id             = msID,
    title          = "Westcott/Hort",
    abbreviation   = "W/H",
    language       = Language('grc'),
    type           = 'Bible',
    osis_slug      = 'WH',
    publish_date   = date(1881, 1, 1),
    originality    = 'manuscript-edition',
    creator        = "By <a href='http://en.wikipedia.org/wiki/Brooke_Foss_Westcott' title='Brooke Foss Westcott @ Wikipedia'>Brooke Foss Westcott</a> and <a href='http://en.wikipedia.org/wiki/Fenton_John_Anthony_Hort' title='Fenton John Anthony Hort @ Wikipedia'>Fenton John Anthony Hort</a>.",
    url            = source_url,
    #variant_number = 1,
    license        = License.objects.filter(url="http://creativecommons.org/licenses/publicdomain/")[0]
)
msWork.save()

varGroup1 = VariantGroup(
    work = msWork,
    primacy = 0
)
varGroup1.save()

# Now we need to create additional works for each set of variants that this work contains
# Diff/variant works will have tokens that have positions that are the same as those in the base work? The base work's tokens will have positions that have gaps?
# When processing a line with enclosed variants, it will be important to construct the verse for VAR1, VAR2, etc... and then merge these together.
#variantWork = Work(
#    id             = varMsID,
#    title          = "UBS4 Variants",
#    abbreviation   = "UBS4-var",
#    language       = Language('grc'),
#    type           = 'Bible',
#    osis_slug      = 'UBS4-var',
#    publish_date   = date(1993, 1, 1),
#    originality    = 'manuscript-edition',
#    creator        = "By <a href='http://en.wikipedia.org/wiki/Eberhard_Nestle' title='Eberhard Nestle @ Wikipedia'>Eberhard Nestle</a>, <a href='http://en.wikipedia.org/wiki/Erwin_Nestle' title='Erwin Nestle @ Wikipedia'>Erwin Nestle</a>, <a href='http://en.wikipedia.org/wiki/Kurt_Aland' title='Kurt Aland @ Wikipedia'>Kurt Aland</a>, <a href='http://www.biblesociety.org/'>United Bible Societies</a> et al",
#    url            = source_url,
#    base           = msWork,
#    #variant_number = 2,
#    license        = License.objects.get(url="http://en.wikipedia.org/wiki/Fair_use")
#)
#variantWork.save()

varGroup2 = VariantGroup(
    work = msWork,
    primacy = 1,
    title = "UBS4 Variants",
    license = License.objects.get(url="http://en.wikipedia.org/wiki/Fair_use")
)
varGroup2.save()

# The followig regular epression identifies the parts of the following line:
# 40N	1	1		10	Βίβλος G976 N-NSF γενέσεως G1078 N-GSF Ἰησοῦ G2424 N-GSM χριστοῦ G5547 N-GSM , υἱοῦ G5207 N-GSM Δαυίδ G1138 N-PRI , υἱοῦ G5207 N-GSM Ἀβραάμ G11 N-PRI .
lineParser = re.compile(ur"""^
        (?P<book>\d+\w+)\t+         # Unbound Bible Code
        (?P<chapter>\d+)\t+         # Chapter
        (?P<verse>\d+)\t+           # Verse
        \d+\t+                      # Ignore orderby column
        (?P<data>.*?)
    \s*$""",
    re.VERBOSE
)

# Regular expression to parse each individual word on a line (the data group from above)
tokenParser = re.compile(ur"""
        \[*(?P<word>ινα\s+τι|\S+?)\]*\s+
        
        (?P<rawParsing>
            G?\d+
            (?:  \s+G?\d+  |  \s+[A-Z0-9\-:]+ | \]  )+
        )
        
        #(?P<strongs1>G?\d+)\]*\s+
        #(?:
        #    G?(?P<strongs2>\d+\]*)\s+
        #)?
        #(?P<parsing>[A-Z0-9\-]+)\]*
        #(?P<extra>
        #    (?:  \s+G?\d+  |  \s+[A-Z0-9\-:]+ | \]  )+
        #)?
        (?:\s+|$)
    """,
    re.VERBOSE | re.UNICODE)

# We need to deal with single variant brackets and double variant brackets; actually, what we need to do is pre-process the entire file and fix the variant brackets
#reMatchVariantString = re.compile(ur"\[\s*([^\]]+\s[^\]]+?)\s*\]") #re.compile(ur"(\[(?!\s)\b\p{Greek}+.+?\p{Greek}\b(?<!\s)\])")

# Compile the regular expressions that are used to isolate the variants for each work
reFilterVar1 = re.compile(ur"\s* ( {VAR[^1]:.+?} | {VAR1: | } )""", re.VERBOSE)
reFilterVar2 = re.compile(ur"\s* ( {VAR[^2]:.+?} | {VAR2: | } )""", re.VERBOSE)
reHasVariant = re.compile(ur'{VAR')
reHasBracket = re.compile(ur'\[|\]')

bookRefs = []
chapterRefs = []
verseRefs = []
tokens = []
previousTokens = []


class TokenContainer:
    "Contains a regular expression match for a work; used for collating two works' variants and merging them together before insertion into model"
    def __init__(self, match, variant_group = None, position = None, open_brackets = 0):
        self.match = match
        self.variant_group = variant_group
        self.position = position
        self.open_brackets = open_brackets
    
    #def __unicode__(self):
    #    s = ('[' * self.open_brackets) + self.match['word'] + (']' * self.open_brackets)
    #    if self.variant_group:
    #        s += '-' + str(self.variant_group.id)
    #    return s
    
    def __hash__(self):
        return hash(self.match['word'])

    def __eq__(self, other):
        return self.match['word'] == other.match['word']

var1OpenBrackets = 0
var2OpenBrackets = 0

tokenPosition = 0

zip = zipfile.ZipFile(os.path.basename(source_url))
for verseLine in StringIO.StringIO(zip.read("greek_WH_UBS4_parsed_utf8.txt")):
    if(verseLine.startswith('#')):
        continue
    verseLine = unicodedata.normalize("NFC", smart_unicode(verseLine))
    verseInfo = lineParser.match(verseLine)
    if(not verseInfo):
        raise Exception("Parse error on line: " + verseLine)
    if(not verseInfo.group('data') or UNBOUND_CODE_TO_OSIS_CODE[verseInfo.group('book')] not in OSIS_BIBLE_BOOK_CODES):
        continue
    meta = verseInfo.groupdict()
    
    tokenContainers = []
    verseTokens = []

    # Parse words for both variants, or if there are open brackets or if this verse has brackets, then we need to do some special processing
    # Regarding two editions having identical variants but differing degrees of assurance: we will have to not insert them as Token(variant_group=None) but rather
    # as two tokens at the same position with different variant_groups and different certainties:
    #  Token(variant_group=1, position=X, certainty=0)
    #  Token(variant_group=2, position=X, certainty=1)
    if((var1OpenBrackets or var2OpenBrackets) or reHasVariant.search(meta['data']) or reHasBracket.search(meta['data'])):
        
        # Get the tokens from the first variant
        verseVar1 = reFilterVar1.sub('', meta['data']).strip()
        verseTokensVar1 = []
        pos = 0
        while(pos < len(verseVar1)):
            tokenMatch = tokenParser.match(verseVar1, pos)
            if(not tokenMatch):
                print "at " + str(pos) + ": " + verseVar1
                raise Exception("Parse error")
            token = TokenContainer(tokenMatch.groupdict(), varGroup1)
            
            # Determine if this token is within brackets
            if(re.search(r'\[\[', verseVar1[tokenMatch.start() : tokenMatch.end()])):
                var1OpenBrackets = 2
            elif(re.search(r'\[', verseVar1[tokenMatch.start() : tokenMatch.end()])):
                var1OpenBrackets = 1
            token.open_brackets = var1OpenBrackets
            
            # Determine if this token is the last one in brackets
            if(re.search(r'\]', verseVar1[tokenMatch.start() : tokenMatch.end()])):
                var1OpenBrackets = 0
            
            verseTokensVar1.append(token)
            pos = tokenMatch.end()
        
        # Get the tokens from the second variant
        verseVar2 = reFilterVar2.sub('', meta['data']).strip()
        verseTokensVar2 = []
        pos = 0
        while(pos < len(verseVar2)):
            tokenMatch = tokenParser.match(verseVar2, pos)
            if(not tokenMatch):
                print "at " + str(pos) + ": " + verseVar2
                raise Exception("Parse error")
            token = TokenContainer(tokenMatch.groupdict(), varGroup2)
            
            # Determine if this token is within brackets
            if(re.search(r'\[\[', verseVar2[tokenMatch.start() : tokenMatch.end()])):
                var2OpenBrackets = 2
            elif(re.search(r'\[', verseVar2[tokenMatch.start() : tokenMatch.end()])):
                var2OpenBrackets = 1
            token.open_brackets = var2OpenBrackets
            
            # Determine if this token is the last one in brackets
            if(re.search(r'\]', verseVar2[tokenMatch.start() : tokenMatch.end()])):
                var2OpenBrackets = 0
            
            verseTokensVar2.append(token)
            pos = tokenMatch.end()
        
        # Now merge verseTokensVar1 and verseTokensVar2 into verseTokens, and then set each token's position according to where it was inserted
        # 'replace'  a[i1:i2] should be replaced by b[j1:j2].
        # 'delete'   a[i1:i2] should be deleted. Note that j1 == j2 in this case.
        # 'insert'   b[j1:j2] should be inserted at a[i1:i1]. Note that i1 == i2 in this case.
        # 'equal'    a[i1:i2] == b[j1:j2] (the sub-sequences are equal).
        # However, we need to not set variant_group to None if the certainty is not the same!!!
        diffedTokenMatches = difflib.SequenceMatcher(None, verseTokensVar1, verseTokensVar2)
        for opcode in diffedTokenMatches.get_opcodes():
            if(opcode[0] == 'equal'):
                var1indicies = range(opcode[1], opcode[2])
                var2indicies = range(opcode[3], opcode[4])
                
                while(len(var1indicies)):
                    i = var1indicies.pop(0)
                    j = var2indicies.pop(0)
                    
                    # Set the position in both var1 and var2 to be the same
                    verseTokensVar1[i].position = tokenPosition
                    verseTokensVar2[j].position = tokenPosition
                    #print verseTokensVar1[i].match['word'] + " == " + verseTokensVar2[j].match['word']
                    
                    # If the two variants are identical even in the open bracket count, then only insert one and set
                    # variant_group to None because there is absolutely no variance
                    if(verseTokensVar1[i].open_brackets == verseTokensVar2[j].open_brackets):
                        verseTokensVar1[i].variant_group = None
                        tokenContainers.append(verseTokensVar1[i])
                    # The open_bracket count in the two tokens is different, so insert both but at the exact same position
                    else:
                        tokenContainers.append(verseTokensVar1[i])
                        tokenContainers.append(verseTokensVar2[j])
                    tokenPosition += 1
            elif(opcode[0] == 'delete'):
                for i in range(opcode[1], opcode[2]):
                    #print "1: " + verseTokensVar1[i].match['word'] + " (delete)"
                    verseTokensVar1[i].position = tokenPosition
                    tokenPosition += 1
                    tokenContainers.append(verseTokensVar1[i])
            elif(opcode[0] == 'insert'):
                for i in range(opcode[3], opcode[4]):
                    #print "2: " + verseTokensVar2[i].match['word'] + " (insert)"
                    verseTokensVar2[i].position = tokenPosition
                    tokenPosition += 1
                    tokenContainers.append(verseTokensVar2[i])
            elif(opcode[0] == 'replace'):
                #print str(verseTokensVar1[opcode[1]] == verseTokensVar2[opcode[3]]) + " THATIS " + (verseTokensVar1[opcode[1]].normalized_word) + " == " + (verseTokensVar2[opcode[3]].normalized_word)
                for i in range(opcode[1], opcode[2]):
                    #print "1: " + verseTokensVar1[i].match['word'] + " (replace)"
                    verseTokensVar1[i].position = tokenPosition
                    tokenPosition += 1
                    tokenContainers.append(verseTokensVar1[i])
                for i in range(opcode[3], opcode[4]):
                    #print "2: " + verseTokensVar2[i].match['word'] + " (replace)"
                    verseTokensVar2[i].position = tokenPosition
                    tokenPosition += 1
                    tokenContainers.append(verseTokensVar2[i])
        
    # No variants and there weren't any variant brackets, so just parse them out of one verse
    else:
        pos = 0
        while(pos < len(meta['data'])):
            tokenMatch = tokenParser.match(meta['data'], pos)
            if(not tokenMatch):
                print "%s %02d %02d" % (verseInfo.group('book'), int(verseInfo.group('chapter')), int(verseInfo.group('verse')))
                print "Unable to parse at position " + str(pos) + ": " + verseInfo.group('data')
                raise Exception("Unable to parse at position " + str(pos) + ": " + verseInfo.group('data'))
            tokenContainers.append(TokenContainer(tokenMatch.groupdict(), None, tokenPosition))
            tokenPosition += 1
            pos = tokenMatch.end()
    
    # Create book ref if it doesn't exist
    if(not len(bookRefs) or bookRefs[-1].osis_id != UNBOUND_CODE_TO_OSIS_CODE[meta['book']]):
        print UNBOUND_CODE_TO_OSIS_CODE[meta['book']]
        
        # Reset tokens
        previousTokens = tokens
        tokens = []
        
        # Close book and chapter refs
        if(len(previousTokens)):
            bookRefs[-1].end_token = previousTokens[-1]
            bookRefs[-1].save()
            chapterRefs[-1].end_token = previousTokens[-1]
            chapterRefs[-1].save()
        chapterRefs = []
        verseRefs = []
        
        # Set up the book ref
        bookRef = Ref(
            work = msWork,
            type = Ref.BOOK,
            osis_id = UNBOUND_CODE_TO_OSIS_CODE[meta['book']],
            position = len(bookRefs),
            title = OSIS_BOOK_NAMES[UNBOUND_CODE_TO_OSIS_CODE[meta['book']]]
        )
        #bookRef.save()
        #bookRefs.append(bookRef)
    
    # Now process the tokens like normal
    verseTokens = []
    
    lastTokenContainer = None
    for tokenContainer in tokenContainers:
        
        # Only do this if the previous token is different than this token
        if not lastTokenContainer or lastTokenContainer.position != tokenContainer.position or lastTokenContainer.match['word'] != tokenContainer.match['word']:
            token = Token(
                data     = tokenContainer.match['word'],
                type     = Token.WORD,
                work     = msWork,
                position = tokenContainer.position,
                #variant_group = tokenContainer.variant_group,
                certainty = tokenContainer.open_brackets
            )
            token.save()
            tokens.append(token)
            verseTokens.append(token)
        
        # Associate the token its respective variant group if it has one
        if tokenContainer.variant_group:
            vgt = VariantGroupToken(
                variant_group = tokenContainer.variant_group,
                token         = tokens[-1],
                certainty     = tokenContainer.open_brackets
            )
            vgt.save()
        
        # Token Parsing
        #strongs = [tokenContainer.match['strongs1']]
        #if(tokenContainer.match['strongs2']):
        #    strongs.append(tokenContainer.match['strongs2'])
        parsing = TokenParsing(
            token = token,
            raw = tokenContainer.match['rawParsing'],
            #parse = tokenContainer.match['parsing'],
            #strongs = ";".join(strongs),
            language = Language('grc'),
            work = msWork
        )
        parsing.save()
        
        # Make this token the first in the book ref, and set the first token in the book
        if len(tokens) == 1:
            bookRef.start_token = tokens[0]
            bookRef.save()
            bookRefs.append(bookRef)
        
        # Set up the Chapter ref
        if(not len(chapterRefs) or chapterRefs[-1].numerical_start != meta['chapter']):
            if(len(chapterRefs)):
                chapterRefs[-1].end_token = tokens[-2]
                chapterRefs[-1].save()
            chapterRef = Ref(
                work = msWork,
                type = Ref.CHAPTER,
                osis_id = ("%s.%s" % (bookRefs[-1].osis_id, meta['chapter'])),
                position = len(chapterRefs),
                parent = bookRefs[-1],
                numerical_start = meta['chapter'],
                start_token = tokens[-1]
            )
            chapterRef.save()
            chapterRefs.append(chapterRef)
        
        lastTokenContainer = tokenContainer
    
    # Create verse ref
    verseRef = Ref(
        work = msWork,
        type = Ref.VERSE,
        osis_id = ("%s.%s.%s" % (bookRefs[-1].osis_id, meta['chapter'], meta['verse'])),
        position = len(verseRefs),
        parent = chapterRefs[-1],
        numerical_start = meta['verse'],
        start_token = verseTokens[0],
        end_token = verseTokens[-1]
    )
    verseRef.save()
    verseRefs.append(verseRef)
    
#Close out the last book and save the chapters
bookRefs[-1].end_token = tokens[-1]
bookRefs[-1].save()
chapterRefs[-1].end_token = tokens[-1]
chapterRefs[-1].save()
#for chapterRef in chapterRefs:
#    chapterRef.save()