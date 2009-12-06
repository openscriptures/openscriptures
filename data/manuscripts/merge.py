#!/usr/bin/env python
# encoding: utf-8
"""
Merging all of the imported (GNT) MSS into a single unified Manuscript.
"""

msID = 8

import sys, os, re, unicodedata, difflib, getopt

from datetime import date
from django.core.management import setup_environ
from django.utils.encoding import smart_str, smart_unicode

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../')) #There's probably a better way of doing this
from openscriptures import settings
setup_environ(settings)
from openscriptures.data.import_helpers import normalize_token
from openscriptures.core.models import *
from django.db.models import Q

forceRebuild = False #overwritten by command line argument
optlist, args = getopt.getopt(sys.argv[1:], '', 'force')
for opt in optlist:
    if(opt[0] == '--force'):
        forceRebuild = True

isIncremental = bool(len(Work.objects.filter(id=msID))) and not forceRebuild #if the unified manuscript already exists

# Get all MSS that will be merged
msWorks = Work.objects.filter(
    Q(originality="manuscript") | Q(originality="manuscript-edition"),
    language=Language('grc'),
    type="Bible"
)

# Note: We should not blow away the existing unified manuscript if there are MSS that haven't been added yet.

# Delete the existing unified manuscript before creating it again
try:
    if(isIncremental):
        umsWork = Work.objects.get(id=msID)
        msWorksUnunified = msWorks.filter(unified=None)
        umsTokensForBooks = {}
        print " + Obtaining all tokens from existing unified manuscript"
        for book_code in OSIS_BIBLE_BOOK_CODES:
            umsTokensForBooks[book_code] = []
            for token in Ref.objects.get(work=umsWork, osis_id=book_code).get_tokens():
                umsTokensForBooks[book_code].append(token)
except:
    print "IM HERE", sys.exc_info()[0]
    isIncremental = False

#print isIncremental
#if(not isIncremental):
#    print "STOP!!"
#    exit()

if(not isIncremental):
    Token.objects.filter(work__in=msWorks).update(unified_token=None) #ON DELETE SET NULL
    Work.objects.filter(unified=msID).update(unified=None) #ON DELETE SET NULL
    Work.objects.filter(id=msID).delete()
    umsWork = Work(
        id             = msID,
        title          = "GNT Unified Manuscript",
        abbreviation   = "GNT-UMS",
        language       = Language('grc'),
        type           = 'Bible',
        osis_slug      = 'GNT-UMS',
        publish_date   = date.today(),
        originality    = 'unified',
        creator        = "Open Scriptures",
        license        = License.objects.get(url="http://creativecommons.org/licenses/by-nc-sa/3.0/")
    )
    umsWork.save()
    msWorksUnunified = msWorks

# Stop now if there aren't any works that haven't been merged already
if(not len(msWorksUnunified)):
    print "(All works manuscripts have already been merged; to force a re-merging, add --force argument)"
    exit()

tokenPosition = 0
bookRefs = []

# Iterate over all books in the New Testament
print "## Merging GNT MSS ##"
for book_code in OSIS_BIBLE_BOOK_CODES:
    print book_code
    
    # If incremental, then just grab the existing unified manuscript
    if(isIncremental):
        umsTokens = umsTokensForBooks[book_code] #umsTokens = Ref.objects.filter(work=umsWork, osis_id=book_code)[0].get_tokens()
        msWorksToMerge = msWorksUnunified
    else:
        # Normalize all tokens in the first manuscript and insert them as the tokens for the UMS
        umsTokens = []
        msWork = msWorksUnunified[0]
        msWork.unified = umsWork
        msWork.save()
        msWorksToMerge = msWorksUnunified[1:]
        if(msWork.base):
            msWorkBase = msWork.base
        else:
            msWorkBase = msWork
        
        print " - " + msWork.title
        tokens = Ref.objects.filter(work=msWorkBase, osis_id=book_code)[0].get_tokens(variant_number = msWork.variant_number)
        for token in tokens:
            umsToken = Token(
                data = normalize_token(token.data),
                type = token.type,
                work = umsWork,
                position = 0 #temporary until merge has been completed; the umsToken's index in umsTokens is its true position
            )
            umsToken.save()
            umsTokens.append(umsToken)
            token.unified_token = umsToken
            token.save()
    
    # Foreach of the MSS then compare with the tokens inserted into the UMS
    for msWork in msWorksToMerge:
        print " - " + msWork.title
        
        msWork.unified = umsWork
        msWork.save()
        
        # Get all tokens from the current manuscipt msWork, and normalize the data (without saving) so that they can be compared with the UMS tokens
        msWorkBase = msWork.base if msWork.base else msWork
        tokens = Ref.objects.get(work=msWorkBase, osis_id=book_code).get_tokens(variant_number = msWork.variant_number)
        for token in tokens:
            token.cmp_data = normalize_token(token.data) #tokens.append(TokenContainer(token))
        newUmsTokens = []
        
        # Now merge tokens and umsTokens to create a new umsTokens
        # 'replace'  a[i1:i2] should be replaced by b[j1:j2].
        # 'delete'   a[i1:i2] should be deleted. Note that j1 == j2 in this case.
        # 'insert'   b[j1:j2] should be inserted at a[i1:i1]. Note that i1 == i2 in this case.
        # 'equal'    a[i1:i2] == b[j1:j2] (the sub-sequences are equal).
        # However, we need to not set variant_number to None if the certainty is not the same!!!
        diffedTokenMatches = difflib.SequenceMatcher(None, tokens, umsTokens)
        for opcode in diffedTokenMatches.get_opcodes():
            # The token in the msWork matches a token in the UMS
            if(opcode[0] == 'equal'):
                i_s = range(opcode[1], opcode[2])
                j_s = range(opcode[3], opcode[4])
                while(len(i_s)):
                    i = i_s.pop(0)
                    j = j_s.pop(0)
                    newUmsTokens.append(umsTokens[j])
                    tokens[i].unified_token = umsTokens[j]
                    tokens[i].save()
            
            # A token in the current manuscript that doesn't exist in the unified Manuscript
            #  and we must insert it into the UMS immediately after the token previously examined
            elif(opcode[0] == 'delete'):
                for i in range(opcode[1], opcode[2]):
                    newUmsTokens.append(Token(
                        work = umsWork,
                        data = normalize_token(tokens[i].data),
                        type = tokens[i].type,
                        position = 0 #temp
                    ))
                    newUmsTokens[-1].save()
                    tokens[i].unified_token = newUmsTokens[-1]
                    tokens[i].save()
            
            # Copy the existing UMS tokens over to the new UMS token list
            elif(opcode[0] == 'insert'):
                for j in range(opcode[3], opcode[4]):
                    newUmsTokens.append(umsTokens[j])
            
            # Insert the tokens that are to replace the ums tokens immediately after
            elif(opcode[0] == 'replace'):
                # Copy the existing UMS tokens over to the new UMS token list
                for j in range(opcode[3], opcode[4]):
                    newUmsTokens.append(umsTokens[j])
                # Insert the new tokens that don't yet existing in the UMS
                for i in range(opcode[1], opcode[2]):
                    newUmsTokens.append(Token(
                        work = umsWork,
                        data = normalize_token(tokens[i].data),
                        type = tokens[i].type,
                        position = 0 #temp
                    ))
                    newUmsTokens[-1].save()
                    tokens[i].unified_token = newUmsTokens[-1]
                    tokens[i].save()
        
        umsTokens = newUmsTokens
    
    # All tokens from all MSS have now been merged into umsTokens, so now the position can be set
    for umsToken in umsTokens:
        umsToken.position = tokenPosition
        umsToken.save()
        tokenPosition = tokenPosition + 1
    
    # Create book ref for the umsTokens
    if(isIncremental):
        bookRef = Ref.objects.get(work=umsWork, osis_id=book_code, type=Ref.BOOK)
        bookRef.start_token = umsTokens[0]
        bookRef.end_token = umsTokens[-1]
    else:
        bookRef = Ref(
            work = umsWork,
            type = Ref.BOOK,
            osis_id = book_code,
            position = len(bookRefs),
            title = OSIS_BOOK_NAMES[book_code],
            start_token = umsTokens[0],
            end_token = umsTokens[-1]
        )
    bookRef.save()
    bookRefs.append(bookRef)
    
    pass