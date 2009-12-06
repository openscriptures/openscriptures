#!/usr/bin/env python
# encoding: utf-8

# TODO: Not inserting refs for TR2, and not inserting enough VGTs

msID = 6
varMsID = 7

import sys, os, re, unicodedata, difflib, urllib, zipfile, StringIO
from datetime import date
from django.core.management import setup_environ
from django.utils.encoding import smart_str, smart_unicode
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../')) #There's probably a better way of doing this
from openscriptures import settings
setup_environ(settings)
from openscriptures.data.unbound_bible import UNBOUND_CODE_TO_OSIS_CODE # Why does this have to be explicit?
from openscriptures.data import import_helpers
from openscriptures.core.models import *

# Abort if MS has already been added (and --force not supplied)
import_helpers.abort_if_imported(msID)

# Download the source file
source_url = "http://www.unboundbible.org/downloads/bibles/greek_textus_receptus_parsed.zip"
import_helpers.download_resource(source_url)

# Delete existing works and their contents
import_helpers.delete_work(msID, varMsID)

msWork = Work(
    id             = msID,
    title          = "Textus Receptus (1551)",
    abbreviation   = "TR-1551",
    language       = Language('grc'),
    type           = 'Bible',
    osis_slug      = 'Steph',
    publish_date   = date(1551, 1, 1),
    originality    = 'manuscript-edition',
    creator        = "By <a href='http://en.wikipedia.org/wiki/Desiderius_Erasmus' title='Desiderius Erasmus @ Wikipedia'>Desiderius Erasmus</a>. Edited by <a href='http://en.wikipedia.org/wiki/Robert_Estienne' title='Robert Estienne @ Wikipedia'>Robert Estienne</a>.",
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
variantWork = Work(
    id             = varMsID,
    title          = "Textus Receptus (1894)",
    abbreviation   = "TR-1894",
    language       = Language('grc'),
    type           = 'Bible',
    osis_slug      = 'Scrivener',
    publish_date   = date(1894, 1, 1),
    originality    = 'manuscript-edition',
    creator        = "By <a href='http://en.wikipedia.org/wiki/Desiderius_Erasmus' title='Desiderius Erasmus @ Wikipedia'>Desiderius Erasmus</a>. Edited by <a href='http://en.wikipedia.org/wiki/Robert_Estienne' title='Robert Estienne @ Wikipedia'>Robert Estienne</a>, and <a href='http://en.wikipedia.org/wiki/Frederick_Henry_Ambrose_Scrivener' title='Frederick Henry Ambrose Scrivener @ Wikipedia'>F. H. A. Scrivener</a>.",
    url            = "http://www.unboundbible.org/downloads/bibles/greek_textus_receptus_parsed.zip",
    base           = msWork,
    #variant_number = 2,
    license        = License.objects.filter(url="http://creativecommons.org/licenses/publicdomain/")[0]
)
variantWork.save()

varGroup2 = VariantGroup(
    work = variantWork,
    primacy = 0
)
varGroup2.save()

works = [msWork, variantWork]
variantGroups = [varGroup1, varGroup2]

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
        (?P<word>ινα\s+τι|\S+)\s+
        (?P<rawParsing>
            G?\d+
            (?:  \s+G?\d+  |  \s+[A-Z0-9\-:]+  )+
        )
        (?:\s+|$)
    """,
    re.VERBOSE | re.UNICODE)

# Compile the regular expressions that are used to isolate the variants for each work
reFilterVar = [
    re.compile(ur"\s* ( {VAR[^1]:.+?} | {VAR1: | } )""", re.VERBOSE),
    re.compile(ur"\s* ( {VAR[^2]:.+?} | {VAR2: | } )""", re.VERBOSE)
]
reHasVariant = re.compile(ur'{VAR')
reHasBracket = re.compile(ur'\[|\]')

bookRefs = [[], []]
chapterRefs = [[], []]
verseRefs = [[], []]
tokens = []


class PlaceholderToken(dict):
    """
    Contains a regular expression match for a work; used for collating two
    works' variants and merging them together before insertion into model
    """
    
    def __init__(self, **args):
        for key in args:
            self[key] = args[key]
    
    def __setattr__(self, key, val):
        self[key] = val
    
    def __getattr__(self, key):
        return self[key]
    
    def establish(self):
        """
        This can take the values and turn this into a real token... and then
        also create the many-to-many relationships. Return the new token?
        """
        
        token = Token(
            data = self.data,
            type = self.type,
            position = self.position,
            certainty = None, #self.certainty; handled by VariantGroupToken
            work = workTNT1
        )
        #for key in self:
        #    if key not in ('variant_group', 'certainty'):
        #        token[key] = self[key]
        token.save()
        
        vgt = VariantGroupToken(
            token = token,
            variant_group = self.variant_group,
            certainty = self.certainty
        )
        vgt.save()
        return token
    
    def __hash__(self):
        return hash(unicode(self))

    def __eq__(self, other):
        return unicode(self) == unicode(other)
    
    #def __str__(self):
    #    return unicode(self)
    def __unicode__(self):
        #return ("[" * self['certainty']) + self['data'] + ("]" * self['certainty'])
        return import_helpers.normalize_token(self['data'])


def verseTokens(): #No need to do generator here?
    """
    Fetch the next token in the verse.
    """
    global works, variantGroups
    previousVerseMeta = {'book':'', 'chapter':'', 'verse':''}
    bookCount         = 0
    chapterCount      = 0
    verseCount        = 0
    openBracketsCount = [0, 0]
    
    zip = zipfile.ZipFile(os.path.basename(source_url))
    for verseLine in StringIO.StringIO(zip.read("greek_textus_receptus_parsed_utf8.txt")):
        if(verseLine.startswith('#')):
            continue
        verseLine = unicodedata.normalize("NFC", smart_unicode(verseLine))
        verseInfo = lineParser.match(verseLine)
        if(not verseInfo):
            raise Exception("Parse error on line: " + verseLine)
        if(not verseInfo.group('data') or UNBOUND_CODE_TO_OSIS_CODE[verseInfo.group('book')] not in OSIS_BIBLE_BOOK_CODES):
            continue
        meta = verseInfo.groupdict()

        newBook, newChapter, newVerse = False, False, False
        if previousVerseMeta['book'] != meta['book']:
            bookCount += 1
            newBook = True
        if previousVerseMeta['book'] != meta['book'] or previousVerseMeta['chapter'] != meta['chapter']:
            chapterCount += 1
            newChapter = True
        if previousVerseMeta['verse'] != meta['verse']:
            verseCount += 1
            newVerse = True
        
        for i in (0,1):
            # Construct the Book ref if it is not the same as the previous
            if newBook:
                print OSIS_BOOK_NAMES[UNBOUND_CODE_TO_OSIS_CODE[meta['book']]]
                bookRef = Ref(
                    type = Ref.BOOK,
                    osis_id = UNBOUND_CODE_TO_OSIS_CODE[meta['book']],
                    title = OSIS_BOOK_NAMES[UNBOUND_CODE_TO_OSIS_CODE[meta['book']]],
                    work = works[i],
                    position = bookCount,
                    #numerical_start = bookCount
                )
                yield bookRef 
            
            # Construct the Chapter ref if it is not the same as the previous or if the book is different (matters for single-chapter books)
            if newChapter:
                chapterRef = Ref(
                    type = Ref.CHAPTER,
                    osis_id = bookRef.osis_id + '.' + meta['chapter'],
                    numerical_start = meta['chapter'],
                    work = works[i],
                    position = chapterCount
                )
                yield chapterRef
            
            # Construct the Verse ref if it is not the same as the previous (note there are no single-verse books)
            if newVerse:
                verseRef = Ref(
                    type = Ref.VERSE,
                    osis_id = chapterRef.osis_id + '.' + meta['verse'],
                    numerical_start = meta['verse'],
                    work = works[i],
                    position = verseCount
                )
                yield verseRef
        
        #end for i in (0,1):
        previousVerseMeta = meta


        # Parse words for both variants, or if there are open brackets or if this verse has brackets, then we need to do some special processing
        # Regarding two editions having identical variants but differing degrees of assurance: we will have to not insert them as Token(variant_group=None) but rather
        # as two tokens at the same position with different variant_groups and different certainties:
        #  Token(variant_group=1, position=X, certainty=0)
        #  Token(variant_group=2, position=X, certainty=1)
        if((openBracketsCount[0] or openBracketsCount[1]) or reHasVariant.search(meta['data']) or reHasBracket.search(meta['data'])):
            
            verseTokensVars = [[], []]
            for i in (0,1):
                verseVar = reFilterVar[i].sub('', meta['data']).strip()
                verseTokensVar = []
                pos = 0
                while(pos < len(verseVar)):
                    tokenMatch = tokenParser.match(verseVar, pos)
                    if not tokenMatch:
                        raise Exception("Parse error")
                    token = PlaceholderToken(
                        data = tokenMatch.group('word'),
                        type = Token.WORD,
                        work = msWork,
                        variant_group = variantGroups[i]
                    )
                    #token = TokenContainer(tokenMatch.groupdict(), 0)
                    
                    # Determine if this token is within brackets
                    if(re.search(r'\[\[', verseVar[tokenMatch.start() : tokenMatch.end()])):
                        openBracketsCount[i] = 2
                    elif(re.search(r'\[', verseVar[tokenMatch.start() : tokenMatch.end()])):
                        openBracketsCount[i] = 1
                    token.certaunty = openBracketsCount[i]
                    
                    # Determine if this token is the last one in brackets
                    if(re.search(r'\]', verseVar[tokenMatch.start() : tokenMatch.end()])):
                        openBracketsCount[i] = 0
                    
                    verseTokensVars[i].append(token)
                    pos = tokenMatch.end()
            
            # Now merge verseTokensVar[0] and verseTokensVar[1] into verseTokens, and then set each token's position according to where it was inserted
            # 'replace'  a[i1:i2] should be replaced by b[j1:j2].
            # 'delete'   a[i1:i2] should be deleted. Note that j1 == j2 in this case.
            # 'insert'   b[j1:j2] should be inserted at a[i1:i1]. Note that i1 == i2 in this case.
            # 'equal'    a[i1:i2] == b[j1:j2] (the sub-sequences are equal).
            # However, we need to not set variant_group to None if the certainty is not the same!!!
            diffedTokenMatches = difflib.SequenceMatcher(None, verseTokensVars[0], verseTokensVars[1])
            for opcode in diffedTokenMatches.get_opcodes():
                if(opcode[0] == 'equal'):
                    var1indicies = range(opcode[1], opcode[2])
                    var2indicies = range(opcode[3], opcode[4])
                    
                    while(len(var1indicies)):
                        i = var1indicies.pop(0)
                        j = var2indicies.pop(0)
                        
                        # If the two variants are identical even in the open bracket count, then only insert one and set
                        # variant_group to None because there is absolutely no variance
                        if(verseTokensVar[0][i].open_brackets == verseTokensVar[1][j].open_brackets):
                            yield verseTokensVar[0][i]
                        # The open_bracket count in the two tokens is different, so insert both but at the exact same position
                        else:
                            yield verseTokensVar[0][i]
                            yield verseTokensVar[1][j]
                elif(opcode[0] == 'delete'):
                    for i in range(opcode[1], opcode[2]):
                        yield verseTokensVar[0][i]
                elif(opcode[0] == 'insert'):
                    for i in range(opcode[3], opcode[4]):
                        yield verseTokensVar[1][i]
                elif(opcode[0] == 'replace'):
                    for i in range(opcode[1], opcode[2]):
                        yield verseTokensVar[0][i]
                    for i in range(opcode[3], opcode[4]):
                        yield verseTokensVar[1][i]
            
        # No variants and there weren't any variant brackets, so just parse them out of one verse
        else:
            pos = 0
            while(pos < len(meta['data'])):
                tokenMatch = tokenParser.match(meta['data'], pos)
                if(not tokenMatch):
                    raise Exception("Unable to parse at position " + str(pos) + ": " + verseInfo.group('data'))
                token = PlaceholderToken(
                    data = tokenMatch.group('word'),
                    type = Token.WORD,
                    work = msWork,
                    variant_group = None
                )
                yield token
                #tokenContainers.append(TokenContainer(tokenMatch.groupdict(), None))
                #tokenContainers.append(TokenContainer(tokenMatch.groupdict(), 0))
                #tokenContainers.append(TokenContainer(tokenMatch.groupdict(), 1))
                pos = tokenMatch.end()
        
    return


count = 0
for token in verseTokens():
    if isinstance(token, Ref):
        print "Ref: " + str(token)
    else:
        print " - " + token.data + " "
    
    count += 1
    if count == 20:
        break;
    
    
    


tokenPosition = 0

exit(1)


























zip = zipfile.ZipFile(os.path.basename(source_url))
for verseLine in StringIO.StringIO(zip.read("greek_textus_receptus_parsed_utf8.txt")):
    if(verseLine.startswith('#')):
        continue
    verseLine = unicodedata.normalize("NFC", smart_unicode(verseLine))
    verseInfo = lineParser.match(verseLine)
    if(not verseInfo):
        raise Exception("Parse error on line: " + verseLine)
    if(not verseInfo.group('data') or UNBOUND_CODE_TO_OSIS_CODE[verseInfo.group('book')] not in OSIS_BIBLE_BOOK_CODES):
        continue
    meta = verseInfo.groupdict()
    
    # Not only do we need to handle {VARX: } but also [variant blocks]
    # Here we need to fix bracketed words (find the span and then add them around each individual word contained in the span)
    
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
            token = TokenContainer(tokenMatch.groupdict(), 0)
            
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
            token = TokenContainer(tokenMatch.groupdict(), 1)
            
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
                    
                    # If the two variants are identical even in the open bracket count, then only insert one and set
                    # variant_group to None because there is absolutely no variance
                    if(verseTokensVar1[i].open_brackets == verseTokensVar2[j].open_brackets):
                        verseTokensVar1[i].variant_group = None
                        verseTokensVar1[i].index = None
                        tokenContainers.append(verseTokensVar1[i])
                    # The open_bracket count in the two tokens is different, so insert both but at the exact same position
                    else:
                        tokenContainers.append(verseTokensVar1[i])
                        tokenContainers.append(verseTokensVar2[j])
            elif(opcode[0] == 'delete'):
                for i in range(opcode[1], opcode[2]):
                    tokenContainers.append(verseTokensVar1[i])
            elif(opcode[0] == 'insert'):
                for i in range(opcode[3], opcode[4]):
                    tokenContainers.append(verseTokensVar2[i])
            elif(opcode[0] == 'replace'):
                for i in range(opcode[1], opcode[2]):
                    tokenContainers.append(verseTokensVar1[i])
                for i in range(opcode[3], opcode[4]):
                    tokenContainers.append(verseTokensVar2[i])
        
    # No variants and there weren't any variant brackets, so just parse them out of one verse
    else:
        pos = 0
        while(pos < len(meta['data'])):
            tokenMatch = tokenParser.match(meta['data'], pos)
            if(not tokenMatch):
                raise Exception("Unable to parse at position " + str(pos) + ": " + verseInfo.group('data'))
            tokenContainers.append(TokenContainer(tokenMatch.groupdict(), None))
            #tokenContainers.append(TokenContainer(tokenMatch.groupdict(), 0))
            #tokenContainers.append(TokenContainer(tokenMatch.groupdict(), 1))
            pos = tokenMatch.end()
    
    # Create book ref if it doesn't exist
    if(not len(bookRefs) or bookRefs[-1].osis_id != UNBOUND_CODE_TO_OSIS_CODE[meta['book']]):
        print UNBOUND_CODE_TO_OSIS_CODE[meta['book']]
        
        # Set up the book ref
        for i in (0,1):
            bookRef = Ref(
                work = works[i],
                type = Ref.BOOK,
                osis_id = UNBOUND_CODE_TO_OSIS_CODE[meta['book']],
                position = len(bookRefs[i]),
                title = OSIS_BOOK_NAMES[UNBOUND_CODE_TO_OSIS_CODE[meta['book']]]
            )
            bookRefs[i].append(bookRef)
    
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