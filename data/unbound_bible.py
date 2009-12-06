UNBOUND_CODE_TO_OSIS_CODE = {
	'01O': "Gen",
	'02O': "Exod",
	'03O': "Lev",
	'04O': "Num",
	'05O': "Deut",
	'06O': "Josh",
	'07O': "Judg",
	'08O': "Ruth",
	'09O': "1Sam",
	'10O': "2Sam",
	'11O': "1Kgs",
	'12O': "2Kgs",
	'13O': "1Chr",
	'14O': "2Chr",
	'15O': "Ezra",
	'16O': "Neh",
	'17O': "Esth",
	'18O': "Job",
	'19O': "Ps",
	'20O': "Prov",
	'21O': "Eccl",
	'22O': "Song",
	'23O': "Isa",
	'24O': "Jer",
	'25O': "Lam",
	'26O': "Ezek",
	'27O': "Dan",
	'28O': "Hos",
	'29O': "Joel",
	'30O': "Amos",
	'31O': "Obad",
	'32O': "Jonah",
	'33O': "Mic",
	'34O': "Nah",
	'35O': "Hab",
	'36O': "Zeph",
	'37O': "Hag",
	'38O': "Zech",
	'39O': "Mal",
	
	'40N': "Matt",
	'41N': "Mark",
	'42N': "Luke",
	'43N': "John",
	'44N': "Acts",
	'45N': "Rom",
	'46N': "1Cor",
	'47N': "2Cor",
	'48N': "Gal",
	'49N': "Eph",
	'50N': "Phil",
	'51N': "Col",
	'52N': "1Thess",
	'53N': "2Thess",
	'54N': "1Tim",
	'55N': "2Tim",
	'56N': "Titus",
	'57N': "Phlm",
	'58N': "Heb",
	'59N': "Jas",
	'60N': "1Pet",
	'61N': "2Pet",
	'62N': "1John",
	'63N': "2John",
	'64N': "3John",
	'65N': "Jude",
	'66N': "Rev",
	
	'67A': "Tob",
	'68A': "Jdt",
	'69A': "AddEsth",
	'70A': "Wis",
	'71A': "Sir",
	'72A': "Baruch",
	'73A': "EpJer",
	'74A': "PrAzar",
	'75A': "Sus",
	'76A': "Bel",
	'77A': "1Macc",
	'78A': "2Macc",
	'79A': "3Macc",
	'80A': "4Macc",
	'81A': "1Esd",
	'82A': "2Esd",
	'83A': "PrMan",
	#'84A': "Psalm 151"
	#'85A': "Psalm of Solomon
	#'86A': "Odes
}


"""
sub parseUnboundVerseLine {
	my $d = shift;
	my $varNum = shift;

	#Keep only the requested variant
	if($varNum){
		$d =~ s/{VAR$varNum:(.+?)}/$1/g;
		$d =~ s/{VAR(?!$varNum)\d+:(.+?)}//g;
	}
	
	#Trim
	$d =~ s/^\s+//;
	$d =~ s/\s+$//;
	
	$d =~ s/
		(\[(?!\s)\b\p{Greek}+.+?\p{Greek}\b(?<!\s)\]) #This needs to be revised: no Greek
	 /
		addVariantBrackets($1)
	 /gxe;
	
	#Parse multiple words on a line
	$d = NFC($d);
	my @results = $d =~ m/
		\s*(\[?\p{Greek}+\]?)   #This needs to be revised: no Greek
		\s+(G0*\d+)
		\s+([A-Z\ 0-9\-]+?)
		(?=\s+\[?\p{Greek}|\s*$|\s*{)   #This needs to be revised: no Greek
	 /gx;
	
	my @tokens;
	for(my $i = 0; $i < @results; $i += 3){
		my $data = $results[$i];
		my $type = 'word';
		my $parsing = $results[$i+1] . ' ' . $results[$i+2];
		my @strongs = $parsing =~ m/([GH]\d+)/g;
		$parsing =~ s{G\d+}{}g;
		$parsing =~ s/^\s+//;
		
		push @tokens, {
			data       => $data,
			type       => $type,
			strongs    => \@strongs,
			#lemma      => $strongsDict{$strongs}->{word},
			#kjv_def    => $strongsDict{$strongs}->{kjv_def},
			#strongs_def => $strongsDict{$strongs}->{strongs_def},
			parse      => $parsing
		};
	}
	return @tokens;
}

sub addVariantBrackets {
	my $s = shift;
	
	$s =~ s/
		(?<!\[)(\b\p{Greek}+)
	 /\[$1/gx;
	
	$s =~ s/
		(\p{Greek}+\b)(?!\])
	 /$1\]/gx;
	
	return $s;
}
"""
