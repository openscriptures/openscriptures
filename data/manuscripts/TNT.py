#!/usr/bin/env python
# encoding: utf-8
"""
Problem: if two of the same words occur together in the original, this will be lost!
"""

TNT1_ID = 10 #TNT
TNT2_ID = 11 #TNT2

import sys, os, re, unicodedata, difflib, zipfile, StringIO
from datetime import date
from django.core.management import setup_environ
from django.utils.encoding import smart_str, smart_unicode
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../')) #There's probably a better way of doing this
from openscriptures import settings
setup_environ(settings)
from openscriptures.core.models import *
from openscriptures.data import import_helpers

# Abort if MS has already been added (or --force not supplied)
import_helpers.abort_if_imported(TNT1_ID)

# Download the source file
source_url = "http://www.tyndalehouse.com/Download/TNT 1.0.0.zip"
var_source_url = "http://www.tyndalehouse.com/Download/TNT2 1.0.0.zip"
#import_helpers.download_resource(source_url)
#import_helpers.download_resource(var_source_url)

# Delete existing works and their contents
import_helpers.delete_work(TNT1_ID, TNT2_ID)

workTNT1 = Work(
    id           = TNT1_ID,
    title        = "Tregelles' Greek New Testament",
    abbreviation = 'Tregelles',
    language     = Language('grc'),
    type         = 'Bible',
    osis_slug    = 'TNT',
    publish_date = date(1879, 1, 1),
    originality  = 'manuscript-edition',
    creator      = "Samuel Prideaux Tregelles, LL.D. Transcription edited by Dirk Jongkind, in collaboration with Julie Woodson, Natacha Pfister, and Robert Crellin. Consultant editor: P.J. Williams. Tyndale House.",
    url          = source_url,
    #variant_number = 1,
    license      = License.objects.get(url="http://creativecommons.org/licenses/by-nc-sa/3.0/")
)
workTNT1.save()

varGroupTNT1 = VariantGroup(
    work = workTNT1,
    primacy = 0
)
varGroupTNT1.save()

varGroupTNT1_Steph = VariantGroup(
    work = workTNT1,
    title = "Stephanus",
    primacy = 1
)
varGroupTNT1_Steph.save()

varGroupTNT1_D = VariantGroup(
    work = workTNT1,
    title = "Codex D",
    primacy = 1
)
varGroupTNT1_D.save()

# The variant work is the corrected edition
workTNT2 = Work(
    id             = TNT2_ID,
    title          = "Tregelles' Corrected Greek New Testament",
    abbreviation   = "Tregelles2",
    language       = Language('grc'),
    type           = 'Bible',
    osis_slug      = 'Tregelles2',
    publish_date   = date(2009, 6, 1),
    originality    = 'manuscript-edition',
    creator        = "Samuel Prideaux Tregelles, LL.D. Transcription edited by Dirk Jongkind, in collaboration with Julie Woodson, Natacha Pfister, and Robert Crellin. Consultant editor: P.J. Williams. Tyndale House.",
    url            = var_source_url,
    base           = workTNT1,
    #variant_number = 2,
    license        = License.objects.get(url="http://en.wikipedia.org/wiki/Fair_use")
)
workTNT2.save()

varGroupTNT2 = VariantGroup(
    work = workTNT2,
    primacy = 0
)
varGroupTNT2.save()

varGroupTNT2_Steph = VariantGroup(
    work = workTNT2,
    title = "Stephanus",
    primacy = 1
)
varGroupTNT2_Steph.save()

varGroupTNT2_D = VariantGroup(
    work = workTNT2,
    title = "Codex D",
    primacy = 1
)
varGroupTNT2_D.save()


"""
What is included are the page-numbers of the print edition, the section and
paragraph breaks (in the printed edition the former are marked by a blank line,
the latter by simple indentation of the first line of the paragraph), the
punctuation of the text, and the accentuation as given by Tregelles. The title
and subscription at the end of each book are also included.
"""

""" http://www.tyndalehouse.com/tregelles/page2.html:
The Greek New Testament,
Edited from Ancient Authorities, with their
Various Readings in Full,
and the
Latin Version of Jerome,

by Samuel Prideaux Tregelles, LL.D.

London.
Samuel Bagster and Sons: Paternoster Row.
C. J. Stewart: King William Street, West Strand.
1857–1879.

Transcription edited by Dirk Jongkind, in collaboration with Julie Woodson, Natacha Pfister, and Robert Crellin. Consultant editor: P.J. Williams

Tyndale House, Cambridge
2009.
"""




TNT_TO_OSIS_BOOK_CODES = {
"Mat":  'Matt',
"Mark": 'Mark',
"Luke": 'Luke',
"John": 'John',
"Acts": 'Acts',
"Rom":  'Rom',
"1Co":  '1Cor',
"2Co":  '2Cor',
"Gal":  'Gal',
"Eph":  'Eph',
"Phi":  'Phil',
"Col":  'Col',
"1Th":  '1Thess',
"2Th":  '2Thess',
"1Ti":  '1Tim',
"2Ti":  '2Tim',
"Tit":  'Titus',
"Phm":  'Phlm',
"Heb":  'Heb',
"Jas":  'Jas',
"1Pet": '1Pet', 
"2Pet": '2Pet',
"1John":'1John',
"2John":'2John',
"3John":'3John',
"Jude": 'Jude',
"Rev":  'Rev'      
}       


reVerseMarker = re.compile(ur"^\$\$\$(?P<book>\w+)\.(?P<chapter>\d+)\.(?P<verse>\d+)", re.VERBOSE)


# Notice: The two works have different reference systems (Mat 23:13), thus we
# need to store separate sets of references, one assigned to TNT1 and the other
# to TNT2; TNT2 would be a variant of TNT1, but instead of inheriting TNT1's
# reference system, TNT2's would be used instead... though both systems would
# refer to the same tokens; this is preferrable to making both TNT1 and TNT2 a
# top level base work because then there would be much duplication and
# furthermore the variant distinctions based solely on diacritics (everything)
# would be lost.
#
# So we have TNT1 and TNT2, and in each of these we have Steph and D, but Steph
# and D don't match up exactly in both So we basically need to have TNT1 as
# base, with TNT2 as derivative work (variant group 2) And then we need Steph
# and D to be variant group sets (2,3), with Steph2 and D2 as Variant group sets
# (3,4)?? How would Steph2 be based on Steph? This is getting too convoluted?
# Unless we merge everything together as originally talked about, and where
# everything agrees we insert a token without a variant group association. But
# if any token is not agreed to by all of the variant groups, then the tokens
# for each variant group must be stored separately (in duplicates) however they
# all share the same position. But is there any way to determine that they are
# duplicates other than by comparing the actual string values? Overwhelmingly
# the tokens will be overlap so there will be fewer tokens stored, and this will
# improve performance and storage space, and will give fewer tokens to be
# linked, but how exactly will such a work be merged with other works? It isn't
# possible to just display one variant group at a time, is it?

files = (
    open("TNT 1.0.0.txt"),
    open("TNT2 1.0.0.txt")
)

verseMeta = [None, None]
verseBuffer = ["", ""]
rawVerses = []
lineNumber  = [0, 0]
for f in files:
    rawVerses.append([])

print "Parsing all of the verses out of the files..."

while True:
    for i in range(0,len(files)):
        if files[i].closed:
            continue
        line = files[i].readline()
        if not line:
            files[i].close()
            continue
        lineNumber[i] += 1
        #line = line.strip()
        if not line: #skip blank line
            continue
        line = unicodedata.normalize("NFC", smart_unicode(line))
        line = line.lstrip(ur"\uFEFF") #REMOVE ZWNB/BOM
        line = line.rstrip()
        #line = re.sub(r"\r?\n$", '', line)
        line = re.sub(ur'<PΒ>', '<PB>', line) #Fix error in $$$Mat.26.55 (Greek B used instead of Latin B)
        line = re.sub(ur'([^> ]+)(<Page.*?>)([^< ]+)', r'\1\3\2', line) #Ensure that Page refs don't break up words: ἔδη<Page = 477>σαν
        #if line2 != line:
        #    print line
        #    print line2
        #    print
        #line = line2
        #<Page[^>]*>[^< \n]
        
        # Ignore <Subsc..>
        line = re.sub(r'<Subsc.*?>', '', line)
        
        # If the the line contains a Title, then it is the beginning of the next
        # book, so push the next raw verse on to reset the buffer
        if line.find('<Title') != -1:
            rawVerses[i].append({
                'meta':None,
                'data':line
            })
            continue
        
        assert(len(rawVerses[i]))
        
        # If this line is a verse marker, save the info and go to the next line
        verseMarkerMatch = reVerseMarker.match(line)
        if(verseMarkerMatch):
            # If the verse meta hasn't been set, then we're at the very beginning
            # of a book, and so we shouldn't push on an extra raw verse, just
            # save the verse meta
            if not rawVerses[i][-1]['meta']:
                rawVerses[i][-1]['meta'] = verseMarkerMatch.groupdict()
                #print ' - ' + verseMarkerMatch.group('book')
            # If we already started into a book, then this verse encountered
            # means that we need to clear the buffer and start a new one
            else:
                # If the previous verse was empty, then eliminate it
                if not rawVerses[i][-1]['data']:
                    rawVerses[i].pop()
                
                rawVerses[i].append({
                    'meta':verseMarkerMatch.groupdict(),
                    'data':''
                })
            continue
        
        
        #Append a space to the previous verse if this verse doesn't begin with
        #if line and len(rawVerses[i]) > 1 and rawVerses[i][-1]['data'] and not re.match(r'^(<(PB|SB)>|\s)', line):
        #    print line
        #    rawVerses[i][-1]['data'] += ' '
        #if len(rawVerses[i]) > 1 and not rawVerses[i][-2]['data'].endswith(" "):
        #    rawVerses[i][-2]['data'] += " "
        
        # Append data to the opened verse buffer
        if line and rawVerses[i][-1]['data'] and not rawVerses[i][-1]['data'].startswith('[D ') and not re.match(ur'^(<.+?>)+$', rawVerses[i][-1]['data']) and not re.match(ur'^(<.+?>)+$', line):
            rawVerses[i][-1]['data'] += "\n"
        rawVerses[i][-1]['data'] += line
    
    if files[0].closed and files[1].closed:
        break

# When all is said and done, the two verse counts should be the same
assert(len(rawVerses[0]) == len(rawVerses[1]))




# Add-in additional whitespace to ends of verses if the following verse is <del>in same book</del>
# does not begin with <SB>, <PB>, or whitespace
for rvv in rawVerses:
    for i in range(0, len(rvv)-1):
        if i+1 >= len(rvv):
            break
        if rvv[i]['data'].startswith('[D ') and not re.match(ur'^(\s|<PB>|<SB>)', rvv[i+1]['data']):
            rvv[i]['data'] = re.sub(ur'(?<=\S)(?=\]\s*\[Steph)', ' ', rvv[i]['data'])
            rvv[i]['data'] = re.sub(ur'(?<=\S)(?=\](?:<.+?>)?$)', ' ', rvv[i]['data'])
        elif not re.match(ur'^(\s|<PB>|<SB>)', rvv[i+1]['data']) and not re.search(ur"\s$", rvv[i]['data']):
            rvv[i]['data'] += ' '



####### Process Verse Contents #####################################################################################################
    


# The meta-data included in the transcription are all within angular brackets < >,
# except for the verse numbering, which is always preceded by $$$ and follows a
# fixed format 10 throughout. Included are page <Page = xxx>, Title <Title = ...>,
# Subscription <Subsc = ...>, Section break <SB>, and Paragraph break <PB>. 

_punctuation = re.escape(ur".·,;:!?()[]")
reToken = re.compile(
    ur"""
     <
       (?P<metaName> SB | PB | Page | Title )
       (\s*=\s*
       (?P<metaValue>.*?)
       \s*)?
     >
    |
        (?P<punctuation> [%s] )
    |
       (?P<word> [^<\s%s]+ )
    |
       (?P<whitespace> \s+ )
    """ % (_punctuation, _punctuation),
    re.VERBOSE | re.UNICODE
)

works = [workTNT1, workTNT2]
variantGroups = [
    varGroupTNT1,
    varGroupTNT1_D,
    varGroupTNT1_Steph,
    varGroupTNT2,
    varGroupTNT2_D,
    varGroupTNT2_Steph
]


class PlaceholderToken(dict):
    """
    Contains a regular expression match for a work; used for collating two
    works' variants and merging them together before insertion into model.
    
    We should use Django 1.1 Proxy here
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


def verseTokens(i): #we could pass in rawVerses[i] here
    """
    Fetch the next token in the verse.
    """
    
    global rawVerses, works, variantGroups
    
    previousVerseMeta = {'book':'', 'chapter':'', 'verse':''}
    bookCount = 0
    chapterCount = 0
    verseCount = 0
    openBracketsCount = 0
    variantsOpenBracketCounts = [0, 0] # 0:D, 1:Steph
    tokenPosition = 0
    
    for verse in rawVerses[i]:
        #Mat.27.11
        #Acts.24.18
        #
        if not TNT_TO_OSIS_BOOK_CODES[verse['meta']['book']] in OSIS_BIBLE_BOOK_CODES:
            continue
        #if verse['meta']['chapter'] != '1':
        #    continue
        #if verse['meta']['verse'] != '10':
        #    continue
        #if verse['meta']['book'] != 'John' or (verse['meta']['chapter'] != '8' ): #and verse['meta']['chapter'] != '7'
        #    continue
        #if verse['meta']['book'] != '1John' or verse['meta']['chapter'] != '4':
        #    continue
        #if verse['meta']['book'] == 'Acts' and verse['meta']['chapter'] == '24' and verse['meta']['verse'] == '18':
        #    okToStart = True
        #if not okToStart:
        #    continue
        #if int(verse['meta']['verse']) not in range(18, 20):
        #    break #stop iteration
        #if not(verse['data'].startswith('[Steph ') or verse['data'].startswith('[D ')):
        #    continue
        #if not verse['data'].count('<Page'):
        #    continue
        #if not verse['data'].count('[['): #if not re.search(r' \[(?!Steph)', verse['data']):
        #    continue
        
        # Construct the Book ref if it is not the same as the previous
        if previousVerseMeta['book'] != verse['meta']['book']:
            print verse['meta']['book']
            bookCount += 1
            bookRef = Ref(
                type = Ref.BOOK,
                osis_id = TNT_TO_OSIS_BOOK_CODES[verse['meta']['book']],
                title = OSIS_BOOK_NAMES[TNT_TO_OSIS_BOOK_CODES[verse['meta']['book']]],
                work = works[i],
                position = bookCount
            )
            
            # Get the book title if it is provided
            titleMatch = re.search(r'<Title\s+=\s*(.+?)>', verse['data'])
            if titleMatch:
                verse['data'] = verse['data'].replace(titleMatch.group(0), '')
                bookRef.title = titleMatch.group(1)
            yield bookRef
        
        # Construct the Chapter ref if it is not the same as the previous or if the book is different (matters for single-chapter books)
        if previousVerseMeta['book'] != verse['meta']['book'] or previousVerseMeta['chapter'] != verse['meta']['chapter']:
            chapterCount += 1
            chapterRef = Ref(
                type = Ref.CHAPTER,
                osis_id = bookRef.osis_id + '.' + verse['meta']['chapter'],
                numerical_start = verse['meta']['chapter'],
                work = works[i],
                position = chapterCount
            )
            print chapterRef.osis_id
            yield chapterRef
        
        # Construct the Verse ref if it is not the same as the previous (note there are no single-verse books)
        if previousVerseMeta['verse'] != verse['meta']['verse']:
            verseCount += 1
            verseRef = Ref(
                type = Ref.VERSE,
                osis_id = chapterRef.osis_id + '.' + verse['meta']['verse'],
                numerical_start = verse['meta']['verse'],
                work = works[i],
                position = verseCount
            )
            yield verseRef
        previousVerseMeta = verse['meta']
        
        # If the verse is Stephanus or Codex D, do a pre-merge #######################################################
        if verse['data'].startswith('[Steph ') or verse['data'].startswith('[D '):
            # Here we have to do merge Steph and D and place into TokenContainers
            
            myVariantGroups = [variantGroups[i*3+1], variantGroups[i*3+2]] # 0:D, 1:Steph
            tokens = [[], []] # 0:D, 1:Steph
            
            #[D και επορευθησαν ἑκαστος εις τον οικον αυτου.] [Steph καὶ ἐπορεύθησαν ἕκαστος εἰς τὸν οἶκον αὐτοῦ.]
            varMatch = re.match(ur'\[D\s*(?P<D>.+)\]\s*\[Steph\s*(?P<Steph>.+)\]\s*(?P<extra><\w.+?>)?\s*$', verse['data'], re.UNICODE | re.DOTALL)
            if not varMatch:
                raise Exception("Unable to parse variant verse set (D & Steph)")
            varVerses = [varMatch.group('D'), varMatch.group('Steph')]
            if varMatch.group('extra'):
                varVerses[1] += varMatch.group('extra')
            
            # Now we parse the tokens from Steph and D and place into the tokens array to merge afterward
            for varIndex in (0,1): # 0:D, 1:Steph
                pos = 0
                verseData = varVerses[varIndex]
                
                while pos < len(verseData):
                    tokenMatch = reToken.match(verseData, pos)
                    if not tokenMatch:
                        raise Exception("Unable to parse at position " + str(pos) + ": " + verseData)
                    
                    # Process whitespace
                    if tokenMatch.group('whitespace'):
                        tokens[varIndex].append(PlaceholderToken(
                            data = tokenMatch.group('whitespace'),
                            type = Token.WHITESPACE,
                            variant_group = myVariantGroups[varIndex],
                            certainty = variantsOpenBracketCounts[varIndex]
                        ))
                
                    
                    # Insert word
                    elif tokenMatch.group('word'):
                        tokens[varIndex].append(PlaceholderToken(
                            data = tokenMatch.group('word'),
                            #work = works[i],
                            type = Token.WORD,
                            variant_group = myVariantGroups[varIndex],
                            certainty = variantsOpenBracketCounts[varIndex]
                        ))
                    
                    # Insert punctuation
                    elif tokenMatch.group('punctuation'):
                        if tokenMatch.group('punctuation') == '[':
                            variantsOpenBracketCounts[varIndex] += 1
                        elif tokenMatch.group('punctuation') == ']':
                            variantsOpenBracketCounts[varIndex] -= 1
                        else:
                            tokens[varIndex].append(PlaceholderToken(
                                data = tokenMatch.group('punctuation'),
                                #work = works[i],
                                type = Token.PUNCTUATION,
                                variant_group = myVariantGroups[varIndex],
                                certainty = variantsOpenBracketCounts[varIndex]
                            ))
                    
                    elif tokenMatch.group('metaName'):
                        # Insert page ref
                        if tokenMatch.group('metaName') == 'Page':
                            #tokens[varIndex].append(PlaceholderToken(
                            #    data = u' PP ',
                            #    type = Token.WHITESPACE,
                            #    variant_group = myVariantGroups[varIndex],
                            #    certainty = variantsOpenBracketCounts[varIndex]
                            #))
                            
                            #raise Exception("CANNOT INSERT PAGE: " + tokenMatch.group('metaValue'))
                            tokens[varIndex].append(Ref(
                                type = Ref.PAGE,
                                position = tokenMatch.group('metaValue'),
                                numerical_start = tokenMatch.group('metaValue'),
                                work = works[i]
                            ))
                        
                        # Insert section 
                        elif tokenMatch.group('metaName') == 'SB':
                            tokens[varIndex].append(PlaceholderToken(
                                data = u"§",
                                #work = works[i],
                                type = Token.PUNCTUATION,
                                variant_group = myVariantGroups[varIndex],
                                certainty = variantsOpenBracketCounts[varIndex]
                            ))
                        
                        # Insert paragraph 
                        elif tokenMatch.group('metaName') == 'PB':
                            tokens[varIndex].append(PlaceholderToken(
                                data = u"¶",
                                #work = works[i],
                                type = Token.PUNCTUATION,
                                variant_group = myVariantGroups[varIndex],
                                certainty = variantsOpenBracketCounts[varIndex]
                            ))
                    
                    pos = tokenMatch.end()

            # Now merge tokens[0] with tokens[1], and the result will be yielded back
            # 'replace'  a[i1:i2] should be replaced by b[j1:j2].
            # 'delete'   a[i1:i2] should be deleted. Note that j1 == j2 in this case.
            # 'insert'   b[j1:j2] should be inserted at a[i1:i1]. Note that i1 == i2 in this case.
            # 'equal'    a[i1:i2] == b[j1:j2] (the sub-sequences are equal).
            # However, we need to not set variant_group to None if the certainty is not the same!!!
            diffedTokenMatches = difflib.SequenceMatcher(None, tokens[0], tokens[1])
            for opcode in diffedTokenMatches.get_opcodes():
                if(opcode[0] == 'equal'):
                    token1indicies = range(opcode[1], opcode[2])
                    token2indicies = range(opcode[3], opcode[4])
                    
                    while(len(token1indicies)):
                        token1index = token1indicies.pop(0)
                        token2index = token2indicies.pop(0)
                        
                        assert(type(tokens[0][token1index]) == type(tokens[1][token2index]))
                        
                        # Set the position in both var1 and var2 to be the same
                        if isinstance(tokens[0][token1index], PlaceholderToken):
                            tokens[0][token1index].position = tokenPosition
                            tokens[1][token2index].position = tokenPosition
                            tokenPosition += 1
                        
                        # (Identical tokens are detected and consolidated later)
                        yield tokens[0][token1index]
                        yield tokens[1][token2index]
                
                elif(opcode[0] == 'delete'):
                    for token1index in range(opcode[1], opcode[2]):
                        if isinstance(tokens[0][token1index], PlaceholderToken):
                            tokens[0][token1index].position = tokenPosition
                            tokenPosition += 1
                        yield tokens[0][token1index]
                
                elif(opcode[0] == 'insert'):
                    for token2index in range(opcode[3], opcode[4]):
                        if isinstance(tokens[1][token2index], PlaceholderToken):
                            tokens[1][token2index].position = tokenPosition
                            tokenPosition += 1
                        yield tokens[1][token2index]
                
                elif(opcode[0] == 'replace'):
                    for token1index in range(opcode[1], opcode[2]):
                        if isinstance(tokens[0][token1index], PlaceholderToken):
                            tokens[0][token1index].position = tokenPosition
                            tokenPosition += 1
                        yield tokens[0][token1index]
                    for token2index in range(opcode[3], opcode[4]):
                        if isinstance(tokens[1][token2index], PlaceholderToken):
                            tokens[1][token2index].position = tokenPosition
                            tokenPosition += 1
                        yield tokens[1][token2index]
            
            
        
        # Simply gather tokens tokens (in tokenContainers) for merging after this loop is complete #########################
        else:
    
            # When do we insert the refs? Best to do after the tokens have been inserted
            # Instead of storing the tokenMatch in the tokenContainer, we could store the
            # the actual Token objects
            pos = 0
            while pos < len(verse['data']):
                tokenMatch = reToken.match(verse['data'], pos)
                if not tokenMatch:
                    raise Exception("Unable to parse at position " + str(pos) + ": " + verse['data'])
                
                # Process whitespace
                if tokenMatch.group('whitespace'):
                    #Note: We should normalize this a bit. If a linebreak appears, then just insert "\n"; otherwise insert " "
                    #data = u" "
                    #if tokenMatch.group('whitespace').find("\n") != None:
                    #    data = u"\n";
                    
                    yield PlaceholderToken(
                        data = tokenMatch.group('whitespace'),
                        work = works[i],
                        type = Token.WHITESPACE,
                        variant_group = variantGroups[i*3],
                        certainty = openBracketsCount,
                        position = tokenPosition
                    )
                    tokenPosition += 1
                
                # Insert word
                elif tokenMatch.group('word'):
                    yield PlaceholderToken(
                        data = tokenMatch.group('word'),
                        work = works[i],
                        type = Token.WORD,
                        variant_group = variantGroups[i*3],
                        certainty = openBracketsCount,
                        position = tokenPosition
                    )
                    tokenPosition += 1
                
                # Insert punctuation
                elif tokenMatch.group('punctuation'):
                    if tokenMatch.group('punctuation') == '[':
                        openBracketsCount += 1
                    elif tokenMatch.group('punctuation') == ']':
                        openBracketsCount -= 1
                    else:
                        yield PlaceholderToken(
                            data = tokenMatch.group('punctuation'),
                            work = works[i],
                            type = Token.PUNCTUATION,
                            variant_group = variantGroups[i*3],
                            certainty = openBracketsCount,
                            position = tokenPosition
                        )
                        tokenPosition += 1
                
                elif tokenMatch.group('metaName'):
                    # Insert page ref
                    if tokenMatch.group('metaName') == 'Page':

                        #yield PlaceholderToken(
                        #    data = u' PP2 ',
                        #    work = works[i],
                        #    type = Token.WHITESPACE,
                        #    variant_group = variantGroups[i*3],
                        #    certainty = openBracketsCount,
                        #    position = tokenPosition
                        #)
                        #tokenPosition += 1
                        
                        yield Ref(
                            type = Ref.PAGE,
                            position = tokenMatch.group('metaValue'),
                            numerical_start = tokenMatch.group('metaValue'),
                            work = works[i]
                        )
                    
                    # Insert section ref
                    elif tokenMatch.group('metaName') == 'SB':
                        yield PlaceholderToken(
                            data = u"§",
                            work = works[i],
                            type = Token.PUNCTUATION,
                            variant_group = variantGroups[i*3],
                            certainty = openBracketsCount,
                            position = tokenPosition
                        )
                        tokenPosition += 1
                    
                    # Insert paragraph ref
                    elif tokenMatch.group('metaName') == 'PB':
                        yield PlaceholderToken(
                            data = u"¶",
                            work = works[i],
                            type = Token.PUNCTUATION,
                            variant_group = variantGroups[i*3],
                            certainty = openBracketsCount,
                            position = tokenPosition
                        )
                        tokenPosition += 1
                
                pos = tokenMatch.end()



# Various variables for bookkeeping
pageRefs    = [[], []]
bookRefs    = [[], []]
chapterRefs = [[], []]
verseRefs   = [[], []]


def insertRef(i, ref):
    if ref.type == Ref.BOOK:
        bookRefs[i].append(ref)
    
    elif ref.type == Ref.CHAPTER:
        chapterRefs[i].append(ref)
        
    elif ref.type == Ref.VERSE:
        verseRefs[i].append(ref)
    
    elif ref.type == Ref.PAGE:
        pageRefs[i].append(ref)
    
    #elif ref.type == Ref.SECTION:
    #    ref.position = len(sectionRefs)
    #    sectionRefs.append(ref)
        
    #elif ref.type == Ref.PARAGRAPH:
    #    ref.position = len(paragraphRefs)
    #    paragraphRefs.append(ref)


finalTokenPosition = 0
tokens = []
previousPlaceholderTokens = []

def insertToken(i, placeholderToken):
    """
    Look behind at the previously inserted tokens to see if any of them 
    have the exact same tokenPosition as this token.position; if so, then
    do not insert a new instance of this token, but rather associate a new
    TokenVariantGroup instance to the previously-matched token
    """
    global finalTokenPosition, tokens, bookRefs, chapterRefs, verseRefs, pageRefs
    normalizedMatchedPreviousToken = None
    
    #If placeholderToken.position is different than previous token, then increment 
    if len(previousPlaceholderTokens) and previousPlaceholderTokens[-1].position != placeholderToken.position:
        finalTokenPosition += 1
    previousPlaceholderTokens.append(placeholderToken)
    
    for previousToken in reversed(tokens):
        # Tokens that have the exact same data or same normalized data, all have same position
        if previousToken.position != finalTokenPosition:
            break
        # If the previous token is exactly the same as this token, then simply add the variantGroup to the existing token
        if (placeholderToken.data) == (previousToken.data):
            vgt = VariantGroupToken(
                token = previousToken,
                variant_group = placeholderToken.variant_group,
                certainty = placeholderToken.certainty
            )
            vgt.save()
            updateRefs(i)
            return
        # If a previous token has the same normalized data as this token, 
        elif (import_helpers.normalize_token(placeholderToken.data)) == (import_helpers.normalize_token(previousToken.data)):
            normalizedMatchedPreviousToken = previousToken
        else:
            print "Position is same (%s) but data is different \"%s\" != \"%s\"!" % (finalTokenPosition, import_helpers.normalize_token(placeholderToken.data), import_helpers.normalize_token(previousToken.data))
            raise Exception("Position is same (%s) but data is different \"%s\" != \"%s\"!" % (finalTokenPosition, import_helpers.normalize_token(placeholderToken.data), import_helpers.normalize_token(previousToken.data)))
    
    # Now take the placeholderToken and convert it into a real token and insert it into the database
    #placeholderToken.certainty = None #Handled by variantGroupToken
    placeholderToken.position = finalTokenPosition
    token = placeholderToken.establish()
    tokens.append(token)
    updateRefs(i)
    

def updateRefs(*ii):
    "Here we need to associate the previously inserted Refs with this token, and then save them"
    global bookRefs, chapterRefs, verseRefs, pageRefs, tokens
    
    for i in ii:
        for refsGroup in (bookRefs[i], chapterRefs[i], verseRefs[i], pageRefs[i]):
            if not len(refsGroup):
                continue
            lastRef = refsGroup[-1]
            
            # If the refClass has not been saved, then the start_token hasn't been set
            if not lastRef.id:
                lastRef.start_token = tokens[-1]
                lastRef.save()
            
            # Set the end_token to the last token parsed
            lastRef.end_token = tokens[-1]
            
            # Set the parent of chapters and verses
            if not lastRef.parent:
                if lastRef.type == Ref.CHAPTER:
                    lastRef.parent = bookRefs[i][-1]
                if lastRef.type == Ref.VERSE:
                    lastRef.parent = chapterRefs[i][-1]


# Grab tokens from TNT1 and TNT2
placeholderTokens = [[], []]
for token in verseTokens(0):
    placeholderTokens[0].append(token)
for token in verseTokens(1):
    placeholderTokens[1].append(token)


# Now merge placeholderTokens[0] and placeholderTokens[1]; remember, the differences are going to
# be in punctuation and in accentation; we need to ensire that placeholderTokens with
# differing accentation are stored in the same position

# Now merge placeholderTokens[0] with placeholderTokens[1], and the result will be yielded back
# 'replace'  a[i1:i2] should be replaced by b[j1:j2].
# 'delete'   a[i1:i2] should be deleted. Note that j1 == j2 in this case.
# 'insert'   b[j1:j2] should be inserted at a[i1:i1]. Note that i1 == i2 in this case.
# 'equal'    a[i1:i2] == b[j1:j2] (the sub-sequences are equal).
# However, we need to not set variant_group to None if the certainty is not the same!!!
print "Merging tokens..."
tokenPosition = 0
previousMergedPlaceholderPositions = [[], []]
diffedTokenMatches = difflib.SequenceMatcher(None, placeholderTokens[0], placeholderTokens[1])
for opcode in diffedTokenMatches.get_opcodes():
    if(opcode[0] == 'equal'):
        token1indicies = range(opcode[1], opcode[2])
        token2indicies = range(opcode[3], opcode[4])
        
        while(len(token1indicies)):
            token1index = token1indicies.pop(0)
            token2index = token2indicies.pop(0)
            
            # Set the position in both var1 and var2 to be the same
            if isinstance(placeholderTokens[0][token1index], Ref):
                insertRef(0, placeholderTokens[0][token1index])
                insertRef(1, placeholderTokens[1][token2index])
            # Otherwise, insert both placeholderTokens but at the same position to indicate that they are alternates of the same
            else:
                assert(import_helpers.normalize_token(placeholderTokens[0][token1index].data) == import_helpers.normalize_token(placeholderTokens[1][token2index].data))
                
                # Only increment the token position if these equal tokens are a different position than the previously seen token
                if len(previousMergedPlaceholderPositions[0]) and previousMergedPlaceholderPositions[0][-1] != placeholderTokens[0][token1index].position:
                    tokenPosition += 1
                elif len(previousMergedPlaceholderPositions[1]) and previousMergedPlaceholderPositions[1][-1] != placeholderTokens[1][token2index].position:
                    tokenPosition += 1
                
                previousMergedPlaceholderPositions[0].append(placeholderTokens[0][token1index].position)
                previousMergedPlaceholderPositions[1].append(placeholderTokens[1][token2index].position)
                
                placeholderTokens[0][token1index].position = tokenPosition
                placeholderTokens[1][token2index].position = tokenPosition

                insertToken(0, placeholderTokens[0][token1index])
                insertToken(1, placeholderTokens[1][token2index])
    
    elif(opcode[0] == 'delete'):
        for token1index in range(opcode[1], opcode[2]):
            if isinstance(placeholderTokens[0][token1index], Ref):
                insertRef(0, placeholderTokens[0][token1index])
            else:
                if len(previousMergedPlaceholderPositions[0]) and previousMergedPlaceholderPositions[0][-1] != placeholderTokens[0][token1index].position:
                    tokenPosition += 1
                previousMergedPlaceholderPositions[0].append(placeholderTokens[0][token1index].position)
                placeholderTokens[0][token1index].position = tokenPosition
                insertToken(0, placeholderTokens[0][token1index])
    
    elif(opcode[0] == 'insert'):
        for token2index in range(opcode[3], opcode[4]):
            if isinstance(placeholderTokens[1][token2index], Ref):
                insertRef(1, placeholderTokens[1][token2index])
            else:
                if len(previousMergedPlaceholderPositions[1]) and previousMergedPlaceholderPositions[1][-1] != placeholderTokens[1][token2index].position:
                    tokenPosition += 1
                previousMergedPlaceholderPositions[1].append(placeholderTokens[1][token2index].position)
                placeholderTokens[1][token2index].position = tokenPosition
                insertToken(1, placeholderTokens[1][token2index])
    
    elif(opcode[0] == 'replace'):
        for token1index in range(opcode[1], opcode[2]):
            if isinstance(placeholderTokens[0][token1index], Ref):
                insertRef(0, placeholderTokens[0][token1index])
            else:
                if len(previousMergedPlaceholderPositions[0]) and previousMergedPlaceholderPositions[0][-1] != placeholderTokens[0][token1index].position:
                    tokenPosition += 1
                previousMergedPlaceholderPositions[0].append(placeholderTokens[0][token1index].position)
                placeholderTokens[0][token1index].position = tokenPosition
                insertToken(0, placeholderTokens[0][token1index])
        for token2index in range(opcode[3], opcode[4]):
            if isinstance(placeholderTokens[1][token2index], Ref):
                insertRef(1, placeholderTokens[1][token2index])
            else:
                if len(previousMergedPlaceholderPositions[1]) and previousMergedPlaceholderPositions[1][-1] != placeholderTokens[1][token2index].position:
                    tokenPosition += 1
                previousMergedPlaceholderPositions[1].append(placeholderTokens[1][token2index].position)
                placeholderTokens[1][token2index].position = tokenPosition
                insertToken(1, placeholderTokens[1][token2index])


# Save all refs now that start_tokens and end_tokens have all been set
for i in (0,1):
    for refsGroup in (bookRefs[i], chapterRefs[i], verseRefs[i], pageRefs[i]):
        for ref in refsGroup:
            ref.save()
    
