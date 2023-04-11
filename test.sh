#!/bin/bash

#未完成部分：
#人群，PHI指数
#sumstat必须是gz

export LANG=en_US.UTF-8
echoType="echo -e"
echoContent() {
	case $1 in
	# 红色
	"red")
		# shellcheck disable=SC2154
		${echoType} "\033[31m${printN}$2 \033[0m"
		;;
		# 天蓝色
	"skyBlue")
		${echoType} "\033[1;36m${printN}$2 \033[0m"
		;;
		# 绿色
	"green")
		${echoType} "\033[32m${printN}$2 \033[0m"
		;;
		# 白色
	"white")
		${echoType} "\033[37m${printN}$2 \033[0m"
		;;
	"magenta")
		${echoType} "\033[31m${printN}$2 \033[0m"
		;;
		# 黄色
	"yellow")
		${echoType} "\033[33m${printN}$2 \033[0m"
		;;
	esac
}
# Help documentation
helpdoc() {
	cat <<EOF
Description:
    - Scoring system based on PRS-CSX software
    - Required extarl softwares:Plink2
    - By fu1139@biox.org.cn

Usage:
    $0 -v <vcf> -g <gwas> 
    sh $0 -v vcf.gz -g gwas.tar.gz 

Required:
    The file supports compression formats with gz, tar.gz and zip as suffixes
    The file format should use tab as delimiter

    -v    raw vcf
    -g    Summary statistics files must have the following contents
          Column order and extra column names make no difference to the results
          
          SNP A1  A2  BETA    P
          rs123   C   A  -0.6 4.7e-01
          1:666:A:G   A  G   -0.2 0.5
          
          or
          SNP A1  A2  OR    P
          rs123   C   A  -0.6 4.7e-01
          1:666:A:G   A  G   -0.2 0.5
    -n    Sample size of the GWAS

Optional:
    -p    Patient id (Multiple samples should be separated by comma
          If not selected, all output)
    -P    The file contains rsid Patient id
          If not selected, all output)
    -s    The file contains rsid
          (For example:rs123456  If not selected, all output)
    -o    Output directory
          If not specified, scripts will use the current time as the output folder to distinguish results
    -N    Order of columns in the same order of the GWAS summary statistics files, separated by comma
    -r    reference panels you need: 1kg or ukbb (All used by default) 
    -T    Set this option if you want to limit the number of threads. The default is to use all threads. Programs that use multithreading include PRSCSx and Plink2
    -i    PARAM_PHI: Global shrinkage parameter phi.  
		  Please follow the specified format, such as 1e2, 1e4	(Multiple PHIs should be separated by comma)
		  If phi is not specified, it will be learnt from the data using a fully Bayesian approach. This usually works well for polygenic traits with very large GWAS sample sizes (hundreds of thousands of subjects).   

Reference:
    Site annotation database: GRCH37
    The software annotated genes: snpeff-5.1-2
    PRScs requires Python packages scipy and h5py installed.
    Frequency of the population: gnomAD.genomes.r2.1.1
    Conversion of mutation sites to BIM file format: PLINK 2.00 alpha
    R packages:tidyverse,readr
    
Comment:
    1:Your result is random, but reproducible, because I set a random seed, which is 1
    2:If you want to specify the sample input method, you can only specify one
    3:PARAM_PHI: For GWAS with limited sample sizes (including most of the current disease GWAS), fixing phi to 1e-2 (for highly polygenic traits) or 1e-4 (for less polygenic traits), or doing a small-scale grid search (e.g., phi=1e-6, 1e-4, 1e-2, 1) to find the optimal phi value in the validation dataset often improves perdictive performance.
    4:The SNP in the summary statistics file is the rs ID, A1 is the effect allele, A2 is the alternative allele, BETA/OR is the effect/odds ratio of the A1 allele, and P is the p-value of the effect. In fact, BETA/OR was used only to determine the direction of the association. Thus, the algorithm would still work if the z score or even +1/-1 indicated the direction of effect in the BETA column.
EOF
}
# 参数传递
while getopts ':v:g:s:p:n:N:r:P:i:T:o:h' opt; do
	case $opt in
	v)
		vcf="$OPTARG"
		;;
	N)
		number="$OPTARG"
		;;
	g)
		gwas="$OPTARG"
		;;
	p)
		patient="$OPTARG"
		;;
	P)
		patienttxt="$OPTARG"
		;;
	h)
		helpdoc
		exit 1
		;;
	n)
		ngwas="$OPTARG"
		;;
    o)
		dirdate="$OPTARG"
		;;
	i)
		phi="$OPTARG"
		;;
	r)
		reference="$OPTARG"
		;;
	T)
		N_THREADS="$OPTARG"
		;;
	s)
		snps="$OPTARG"
		;;
	?)
		echoContent red "Unknown parameter"
		exit 1
		;;
	esac
done

# 如果不指定参数，则输出帮助文档
if [ $# -le 0 ]; then
	helpdoc
	exit 1
fi

#必须同时输入 -g 和 -v 参数
if [ -n "${gwas}" ]; then
	[ -z "${vcf}" ] && echoContent red "Missing parameters" && echoContent red "\nPlease provide vcf file and GWAS result  -v" && exit 1
fi
if [ -n "${vcf}" ]; then
	[ -z "${gwas}" ] && echoContent red "Missing parameters" && echoContent red "\nPlease provide vcf file and GWAS result  -g" && exit 1
fi

if [ -z "${ngwas}" ]; then
	echoContent red "Missing parameters" && echoContent red "\nPlease provide sample sizes of the GWAS -n" && exit 1
fi
if [ -n "${reference}" ]; then
	if [[ $reference != "ukbb" && $reference != "1kg" ]]; then
		echoContent red "\nPlease provide right LD reference panel -r"
		exit 1
	fi
else
	declare +a reference
	reference=("ukbb" "1kg")
fi






starttime=$(date +'%Y-%m-%d %H:%M:%S')
echoContent skyBlue "The parameter values you provided are $* \n"

if [ -z "${dirdate}" ]; then
    echoContent skyBlue "You did not specify the output directory, so the script will use the current time as the output folder to distinguish between them"  && dirdate=$(date +%Y%m%d)_$(date +%H%M%S)
fi

mkdir $dirdate

echo "The parameter values you provided are $* \n" >$dirdate/readme


#检查缓存文件和缓存目录
for item in {"$dirdate"/tmp"","$dirdate"/result""}; do
	if [ -f "$item" ]; then
		echoContent red "Please move or rename the file called '$item' in the current directory, because the cache file of this software will be saved in the '$item' folder."
		exit 1
	elif [ ! -d "$item" ]; then
		mkdir -p "$item"
	elif [ "$(ls -A "$item")" != "" ]; then
		echoContent red "Please delete the contents of the folder called '$item' in the current directory, because the software will automatically create the '$item' folder and save the cache file into it"
		exit 1
	else
		echoContent red "Please delete the folder called '$item' in the current directory, because the software will automatically create the '$item' folder and save the cache file into it"
		exit 1
	fi
done
echoContent green "$(date "+%D  %H:%M:%S")"
echoContent green "Preview GWAS file:"

# 检查列名是否正确，检查是否自定义规定列的顺序

if [ -n "${number}" ]; then
	check_gwas_colname() {
		if [[ $2 == 1 ]]; then
			tmp_variable=$(zcat "$1" | head -n 1)
		else
			tmp_variable=$(head <"$1" -n 1)
		fi
		number_of_columns=$(echo "$tmp_variable" | awk 'BEGIN{FS=" ";OFS="\t"}{print NF}')
		array=(${3//,/ })
		length=${#array[*]}
		if [[ $length != "5" ]]; then
			echoContent red "\nPlease provide five full column to match the GWAS statistics\nYou also can use the option -h to see the usage in the help documentation"
			exit 1
		fi
		for item in ${array[@]}; do
			if [[ ! ${item} =~ ^[1-9][0-9]?$ ]]; then
				echoContent red "\nPlease provide five column numbers, separated by commas\nYou also can use the option -h to see the usage in the help documentation"
				exit 1
			elif [ "${item}" -gt "$number_of_columns" ]; then
				echo "The column number you entered is: ${item}"
				echo "The max column number of the file is: $number_of_columns"
				echoContent red "\nPlease make sure that the column number you provide is not greater than the total number of columns in your file\nIf you are sure there is no problem, please change your input file to tab delimited (the software default input file is tab).\nYou also can use the option -h to see the usage in the help documentation"
				exit 1
			fi
		done

		for ((i = 1; i < length; i++)); do
			for ((a = i + 1; a <= length; a++)); do
				[[ "${array[i - 1]}" == "${array[a - 1]}" ]] && echoContent red "\nPlease provide five different column numbers to match GWAS statistics\nYou also can use the option -h to see the usage in the help documentation" && exit 1
			done
		done
		customized_number=1
	}
else
	check_gwas_colname() {
		a=(SNP A1 A2 P)
		b=(BETA OR)
		#echo ${#a[*]}
		if [[ $2 == 1 ]]; then
			c=$(zcat "$1" | head -n 1)
		else
			c=$(head <"$1" -n 1)
		fi
		for var in "${a[@]}"; do
			if [[ ${c[*]/${var}/} == "${c[*]}" ]]; then
				echoContent skyBlue "You have filled in the wrong column name, please use the option -h to see the usage in the help documentation"
				exit 1
			fi
		done
		if [ "${c[*]/${b[0]}/}" = "${c[*]}" ] && [ "${c[*]/${b[1]}/}" = "${c[*]}" ]; then
			echoContent skyBlue "The GWAS file you provided does not contain BETA or OR\nplease use the option -h to see the usage in the help documentation"
			exit 1
		elif [ "${c[*]/${b[0]}/}" != "${c[*]}" ] && [ "${c[*]/${b[1]}/}" != "${c[*]}" ]; then
			echoContent skyBlue "You entered both BETA and OR, keep it unique\nplease use the option -h to see the usage in the help documentation"
			exit 1
		fi
	}
fi

# 解压文件(如果需要)，判断文件是否是 压缩包compression0是tar.gz和正常文件。1是gz，2是zip，compression状态码决定解压或预览文件格式
compression=1
if [ "${gwas##*.}"x = "gz"x ]; then
	tmp="${gwas%.*}"
	if [ "${tmp##*.}"x = "tar"x ]; then
		check_gwas_colname "$gwas" "$compression" "$number"
		compression=0
		tar -xzf "$gwas"
		gwas=${gwas%.*}
		gwas=${gwas%.*}
	else
		check_gwas_colname "$gwas" "$compression" "$number"
	fi

elif [ "${gwas##*.}"x = "zip"x ]; then
	check_gwas_colname "$gwas" "$compression" "$number"
	unzip "$gwas"
	gwas=${gwas%.*}
	compression=2
else
	compression=0
	check_gwas_colname "$gwas" "$compression" "$number"
fi
for item in $vcf; do
	if [ "${item##*.}"x = "gz"x ]; then
		tmp="${item%.*}"
		if [ "${tmp##*.}"x = "tar"x ]; then
			echoContent skyBlue "\nUnzipping vcf file:"
			tar -xzvf "$item"
			vcf=${vcf%.*}
			vcf=${vcf%.*}
		else
			echoContent skyBlue "Unzipping vcf file:"
			gunzip "$item" -c >"${item%.*}"
			vcf=${vcf%.*}
		fi
	elif [ "${item##*.}"x = "zip"x ]; then
		echoContent skyBlue "Unzipping vcf file:"
		unzip "$item"
		vcf=${vcf%.*}
		#else
		#echoContent skyBlue "Copying vcf with a symlink:"
		# path=$(ls $vcf | sed "s:^:$PWD/:")
		# ln -s $path $dirdate/
	fi
done

#解压gwas文件到tmp，整理格式，判断是否自行提供列号，判断是否是压缩包
array=(${number//,/ })

SNP=${array[0]}
A1=${array[1]}
A2=${array[2]}
BETA_OR=${array[3]}
P=${array[4]}

#echoContent green "Preview GWAS file:"
sed_name() {
	sed 's/[0-9A-Za-z]*SNP[0-9A-Za-z]*/SNP/' | sed 's/[0-9A-Za-z]*A1[0-9A-Za-z]*/A1/' | sed 's/[0-9A-Za-z]*A2[0-9A-Za-z]*/A2/' | sed 's/[0-9A-Za-z]*OR[0-9A-Za-z]*/OR/' | sed 's/[0-9A-Za-z]*BETA[0-9A-Za-z]*/BETA/'
}

if [ -n "${customized_number}" ]; then #判断是否自行提供列号
	if [[ $compression == 1 ]]; then #判断是否是压缩包
		zcat "$gwas" | awk -v SNP="$SNP" -v A1="$A1" -v A2="$A2" -v BETA_OR="$BETA_OR" -v P="$P" 'BEGIN {FS=OFS="\t"} {print $SNP,$A1,$A2,$BETA_OR,$P }' | head -n 3 | sed '1c SNP\tA1\tA2\tOR_BETA\tP'
		zcat "$gwas" | awk -v SNP="$SNP" -v A1="$A1" -v A2="$A2" -v BETA_OR="$BETA_OR" -v P="$P" 'BEGIN {FS=OFS="\t"} {print $SNP,$A1,$A2,$BETA_OR,$P }' >$dirdate/tmp_gwas
		sed -i '1c SNP\tA1\tA2\tOR_BETA\tP' $dirdate/tmp_gwas
	else
		awk -v SNP="$SNP" -v A1="$A1" -v A2="$A2" -v BETA_OR="$BETA_OR" -v P="$P" 'BEGIN {FS=OFS="\t"} {print $SNP,$A1,$A2,$BETA_OR,$P }' "$gwas" | head -n 3 | sed '1c SNP\tA1\tA2\tOR_BETA\tP'
		awk -v SNP="$SNP" -v A1="$A1" -v A2="$A2" -v BETA_OR="$BETA_OR" -v P="$P" 'BEGIN {FS=OFS="\t"} {print $SNP,$A1,$A2,$BETA_OR,$P }' "$gwas" >$dirdate/tmp_gwas
		sed -i '1c SNP\tA1\tA2\tOR_BETA\tP' $dirdate/tmp_gwas
	fi
else #判断没有指定列数的时候文件输出到tmp ，此处无法判断P值其他情况，P值必须正确输入，其余只要包含就可以，如SNP121,另外：此处判断逻辑是先判断BETA，没有的话才去找OR   #判断是否自行提供列号
	if [[ $compression == 1 ]]; then

		zcat "$gwas" | head -n 3 | sed_name | awk 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ( "BETA" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["BETA"],$a["P"] ;else if ( "OR" in a)  print $a["SNP"],$a["A1"],$a["A2"],$a["OR"],$a["P"] }'
		number_of_columns=$(zcat "$gwas" | head -n 3 | sed_name | awk 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ( "BETA" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["BETA"],$a["P"] ;else if ( "OR" in a)  print $a["SNP"],$a["A1"],$a["A2"],$a["OR"],$a["P"] }' | head -n 1 | awk '{print NF}')
		if [[ $number_of_columns -ne 5 ]]; then
			echoContent red "There is a problem with the column name of your GWAS file."
			echoContent red "Please correct it yourself or select the -N option, which is specified by the number of columns."
			echoContent red "For details, see -h for help"
			exit 1
		fi
		zcat "$gwas" | head -n 1 | sed_name | grep "BETA" >/dev/null 2>&1
		if [[ $? -ne 1 ]]; then
			zcat "$gwas" | sed_name | awk 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ( "BETA" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["BETA"],$a["P"] }' >$dirdate/tmp_gwas
			sed -i '1c SNP\tA1\tA2\tBETA\tP' $dirdate/tmp_gwas
		else
			zcat "$gwas" | sed_name | awk 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ( "OR" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["OR"],$a["P"] }' >$dirdate/tmp_gwas
			sed -i '1c SNP\tA1\tA2\tOR\tP' $dirdate/tmp_gwas
		fi
	else
		sed -i 's/[0-9A-Za-z]*SNP[0-9A-Za-z]*/SNP/' "$gwas"
		sed -i 's/[0-9A-Za-z]*A1[0-9A-Za-z]*/A1/' "$gwas"
		sed -i 's/[0-9A-Za-z]*A2[0-9A-Za-z]*/A2/' "$gwas"
		sed -i 's/[0-9A-Za-z]*OR[0-9A-Za-z]*/OR/' "$gwas"
		sed -i 's/[0-9A-Za-z]*BETA[0-9A-Za-z]*/BETA/' "$gwas"
		awk <"$gwas" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ("BETA" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["BETA"],$a["P"] ;else if ("OR" in a)  print $a["SNP"],$a["A1"],$a["A2"],$a["OR"],$a["P"] }' | head -n 3
		number_of_columns=$(awk <"$gwas" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ("BETA" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["BETA"],$a["P"] ;else if ("OR" in a)  print $a["SNP"],$a["A1"],$a["A2"],$a["OR"],$a["P"] }' | head -n 1 | awk '{print NF}')
		if [[ $number_of_columns -ne 5 ]]; then
			echoContent red "There is a problem with the column name of your GWAS file."
			echoContent red "Please correct it yourself or select the -N option, which is specified by the number of columns."
			echoContent red "For details, see -h for help"
			exit 1
		fi
		zcat "$gwas" | head -n 1 | sed_name | grep "BETA" >/dev/null 2>&1
		if [[ $? -ne 1 ]]; then
			awk <"$gwas" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ( "BETA" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["BETA"],$a["P"] }' >$dirdate/tmp_gwas
			sed -i '1c SNP\tA1\tA2\tBETA\tP' $dirdate/tmp_gwas
		else
			awk <"$gwas" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{ if ( "OR" in a) print $a["SNP"],$a["A1"],$a["A2"],$a["OR"],$a["P"] }' >$dirdate/tmp_gwas
			sed -i '1c SNP\tA1\tA2\tOR\tP' $dirdate/tmp_gwas
		fi
	fi
fi
echoContent green "$(date "+%D  %H:%M:%S")"
echoContent skyBlue "File format check completed \n"

# 判断是否指定病人ID，如指定则判断数量
if [ -n "$patient" ]; then
	length=$(echo "$patient" | awk -F "," '{print NF}')
	for i in ${patient//,/ }; do
		name=$(grep -v "##" "$vcf" | head -n 1)
		if ! [[ $name =~ $i ]]; then
			echoContent red "The patient number you entered $i is not in the VCF file. Please correct it and try again"
			exit 1
		fi
	done
	if [[ $length -eq 1 ]]; then
		grep -v "##" "$vcf" | awk -v patient="$patient" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{print $a["#CHROM"],$a["POS"],$a["ID"],$a["REF"],$a["ALT"],$a["QUAL"],$a["FILTER"],$a["INFO"],$a["FORMAT"],$a[patient]}' >$dirdate/vcf_noheader_patient
	else
		echoContent skyBlue "你输入了$length个病人"
		grep -v "##" "$vcf" | awk 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{print $a["#CHROM"],$a["POS"],$a["ID"],$a["REF"],$a["ALT"],$a["QUAL"],$a["FILTER"],$a["INFO"],$a["FORMAT"]}' >$dirdate/vcf_noheader
		for i in ${patient//,/ }; do
			grep -v "##" "$vcf" | awk -v patient="$i" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{print $a[patient]}' >$dirdate/vcf_patient_"$i"
		done
		paste $dirdate/vcf_noheader $dirdate/vcf_patient* >$dirdate/vcf_noheader_patient
	fi
fi

if [ -n "$patienttxt" ]; then
	length=$(wc -l $patienttxt | cut -f 1 -d " ")
	while read line; do
		name=$(grep -v "##" "$vcf" | head -n 1)
		if ! [[ $name =~ $line ]]; then
			echoContent red "The patient number you entered $line is not in the VCF file. Please correct it and try again"
			exit 1
		fi
	done <$patienttxt

	if [[ $length -eq 1 ]]; then
		grep -v "##" "$vcf" | awk -v patient="$(cat $patienttxt)" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{print $a["#CHROM"],$a["POS"],$a["ID"],$a["REF"],$a["ALT"],$a["QUAL"],$a["FILTER"],$a["INFO"],$a["FORMAT"],$a[patient]}' >$dirdate/vcf_noheader_patient
	else
		echoContent skyBlue "你输入了$length个病人"
		grep -v "##" "$vcf" | awk 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{print $a["#CHROM"],$a["POS"],$a["ID"],$a["REF"],$a["ALT"],$a["QUAL"],$a["FILTER"],$a["INFO"],$a["FORMAT"]}' >$dirdate/vcf_noheader
		while read line; do
			grep -v "##" "$vcf" | awk -v patient="$line" 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++){a[$i]=i}}NR>=1{print $a[patient]}' >$dirdate/vcf_patient_"$line"
		done <$patienttxt
		paste $dirdate/vcf_noheader $dirdate/vcf_patient* >$dirdate/vcf_noheader_patient
	fi
fi

if [ -n "${patient}" ]; then
	[ -n "${patienttxt}" ] && echoContent skyBlue "You can specify only one type of sample input" && exit 1
fi
if [ -z "${patient}" ]; then
	[ -z "${patienttxt}" ] && echoContent skyBlue "You did not specify the sample, so the default is to output all the sample information" && grep -v "##" "$vcf" >$dirdate/vcf_noheader_patient
fi

echoContent green "$(date "+%D  %H:%M:%S")"
echoContent skyBlue "Now start to replace the rs_id."
sed '1d' $dirdate/tmp_gwas | awk '{print $0,((0-$4)),$1}' | awk 'BEGIN {OFS=FS=":"} {print $1,$2,$3,$4,$5,$7,$6 }' | sed 's/ /\t/g' >$dirdate/tmp_gwas_all
cut -f 3 $dirdate/vcf_noheader_patient >$dirdate/tmp_rsid_snp
cut -f 1 $dirdate/tmp_gwas_all >>$dirdate/tmp_rsid_snp
cut -f 7 $dirdate/tmp_gwas_all | grep ":" >>$dirdate/tmp_rsid_snp
sort -u $dirdate/tmp_rsid_snp >$dirdate/tmp_rsid_snp1

awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$2]=$1;next} NR>=FNR  {if ($1 in a ) {print a[$1],$1}  }' /home/fuyongsheng1139/refdata/UKBall.snp $dirdate/tmp_rsid_snp1 >$dirdate/rsid_snp
awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$2]=$1;next} NR>=FNR  {if ($1 in a ) {print a[$1],$2,$3,$4,$5}  else if ($7 in a) {print a[$7],$3,$2,$6,$5}  else if ($1 ~ /^rs/) {print $1,$2,$3,$4,$5} }' $dirdate/rsid_snp $dirdate/tmp_gwas_all >$dirdate/tmp_gwas_all_snp

head -n 1 $dirdate/tmp_gwas | grep "BETA" >/dev/null 2>&1
if [[ $? -ne 1 ]]; then
	sed -i '1c SNP\tA1\tA2\tBETA\tP' $dirdate/tmp_gwas_all_snp
else
	sed -i '1c SNP\tA1\tA2\tOR\tP' $dirdate/tmp_gwas_all_snp
fi

awk 'BEGIN{OFS=FS="\t"}NR==FNR{a[$2]=$1;next}NR>FNR{if($3 in a) {$3=a[$3];print $0} else if ($3 ~ /^rs/)print $0}' $dirdate/rsid_snp $dirdate/vcf_noheader_patient >$dirdate/vcf_noheader_patient_snp
head -n 1 $dirdate/vcf_noheader_patient | awk '{$1=$2=$4=$5=$6=$7=$8=$9="";print $0}' | sed 's/[ ][ ]//g;s/[ ][ ][ ][ ][ ][ ][ ]/[ ]/g;s/[ ]/\t/g' >$dirdate/vcf_header
head $dirdate/vcf_noheader_patient -n 1 >$dirdate/vcfheader
cat $dirdate/vcfheader $dirdate/vcf_noheader_patient_snp >$dirdate/vcf_header_patient_snp
echoContent green "$(date "+%D  %H:%M:%S")"
echoContent skyBlue "Now start using plink2 to convert the bim \n"

if [ -n "$N_THREADS" ]; then
	/home/fuyongsheng1139/PGT_P_145/ref/plink2 --vcf $dirdate/vcf_header_patient_snp --threads $N_THREADS --make-bed --out $dirdate/bim
else
	/home/fuyongsheng1139/PGT_P_145/ref/plink2 --vcf $dirdate/vcf_header_patient_snp --make-bed --out $dirdate/bim
fi
#纯杂合提取，判断指定位点的情况，合并位点和样本
awk '{$1=$2=$4=$5=$6=$7=$8=$9="";print $0}' $dirdate/vcf_noheader_patient_snp | sed 's/[ ][ ]//g;s/[ ][ ][ ][ ][ ][ ][ ]/[ ]/g;s/[ ]/\t/g' | awk 'BEGIN{OFS=FS="\t"}{for(i=2;i<=NF;i++)gsub(":.*","",$i);print}' | grep -v "\." | sed 's/0\/1/1/g' | sed 's/1\/1/2/g' | sed 's/0\/0/0/g' >$dirdate/patient

#PRSCSX

echoContent green "$(date "+%D  %H:%M:%S")"
echoContent skyBlue "Now start to PRScsx."

length=$(echo "${reference[@]}" | awk -F "," '{print NF}')
for i in ${reference//,/ }; do
	name="ukbb,1kg"
	if ! [[ $name =~ $i ]]; then
		echoContent red "The reference data name you entered $i is not right. Please correct it and try again"
		exit 1
	fi
done

#phi判断
if [ -n "$N_THREADS" ]; then
	export MKL_NUM_THREADS=$N_THREADS
	export NUMEXPR_NUM_THREADS=$N_THREADS
	export OMP_NUM_THREADS=$N_THREADS
	if [[ $length == "1" ]]; then #判断不同的参考gwas结果卡住了
		python /home/fuyongsheng1139/refdata/PRScsx/PRScsx.py --ref_dir=/home/fuyongsheng1139/refdata/PRScsx/ref/"$reference"/ --bim_prefix=$dirdate/bim --sst_file=$dirdate/tmp_gwas_all_snp --n_gwas="$ngwas" --pop=EAS --out_dir=$dirdate/tmp --out_name=result_"$reference" --seed=1
		ls $dirdate/tmp/result*chr* | xargs -I {} cat {} | cut -f 2,6 >$dirdate/tmp_result
	else
		python /home/fuyongsheng1139/refdata/PRScsx/PRScsx.py --ref_dir=/home/fuyongsheng1139/refdata/PRScsx/ref/ukbb/ --bim_prefix=$dirdate/bim --sst_file=$dirdate/tmp_gwas_all_snp --n_gwas="$ngwas" --pop=EAS --out_dir=$dirdate/tmp --out_name=result_ukbb --seed=1
		ls $dirdate/tmp/result*ukbb*chr* | xargs -I {} cat {} | cut -f 2,6 >$dirdate/tmp_result_ukbb
		python /home/fuyongsheng1139/refdata/PRScsx/PRScsx.py --ref_dir=/home/fuyongsheng1139/refdata/PRScsx/ref/1kg/ --bim_prefix=$dirdate/bim --sst_file=$dirdate/tmp_gwas_all_snp --n_gwas="$ngwas" --pop=EAS --out_dir=$dirdate/tmp --out_name=result_1kg --seed=1
		ls $dirdate/tmp/result*1kg*chr* | xargs -I {} cat {} | cut -f 2,6 >$dirdate/tmp_result_1kg
	fi
else
	if [[ $length == "1" ]]; then #判断不同的参考gwas结果卡住了
		python /home/fuyongsheng1139/refdata/PRScsx/PRScsx.py --ref_dir=/home/fuyongsheng1139/refdata/PRScsx/ref/"$reference"/ --bim_prefix=$dirdate/bim --sst_file=$dirdate/tmp_gwas_all_snp --n_gwas="$ngwas" --pop=EAS --out_dir=$dirdate/tmp --out_name=result_"$reference" --seed=1
		ls $dirdate/tmp/result*chr* | xargs -I {} cat {} | cut -f 2,6 >$dirdate/tmp_result
	else
		python /home/fuyongsheng1139/refdata/PRScsx/PRScsx.py --ref_dir=/home/fuyongsheng1139/refdata/PRScsx/ref/ukbb/ --bim_prefix=$dirdate/bim --sst_file=$dirdate/tmp_gwas_all_snp --n_gwas="$ngwas" --pop=EAS --out_dir=$dirdate/tmp --out_name=result_ukbb --seed=1
		ls $dirdate/tmp/result*ukbb*chr* | xargs -I {} cat {} | cut -f 2,6 >$dirdate/tmp_result_ukbb
		python /home/fuyongsheng1139/refdata/PRScsx/PRScsx.py --ref_dir=/home/fuyongsheng1139/refdata/PRScsx/ref/1kg/ --bim_prefix=$dirdate/bim --sst_file=$dirdate/tmp_gwas_all_snp --n_gwas="$ngwas" --pop=EAS --out_dir=$dirdate/tmp --out_name=result_1kg --seed=1
		ls $dirdate/tmp/result*1kg*chr* | xargs -I {} cat {} | cut -f 2,6 >$dirdate/tmp_result_1kg
	fi
fi

runtime() {
	echoContent green "$(date "+%D  %H:%M:%S")"
	echoContent skyBlue "Congratulations, the data processing has been completed."
	echoContent skyBlue "Your results are in the result folder."
	echoContent skyBlue "The result file has two lines, the first line is the sample name, and the second line is the result of polygenic risk score"
	start_seconds=$(date --date="$starttime" +%s)
	end_seconds=$(date --date="$endtime" +%s)
	echoContent skyBlue "本次运行时间： "$(((end_seconds - start_seconds) / 60))"mins"
	echoContent skyBlue "All your final results  are in $dirdate "
}

awk '$1 ~/^rs/ {print $1}' $dirdate/patient | sort | uniq >$dirdate/tmp_patient_snp
if [ -n "${snps}" ]; then
	awk '$1 ~/^rs/ {print $1}' "$snps" sort | uniq >$dirdate/snp
	if [[ $length == "1" ]]; then
		awk '$1 ~/^rs/ {print $1}' $dirdate/tmp_result | sort | uniq >$dirdate/tmp_result_snp
		sort -m $dirdate/snp $dirdate/tmp_result_snp $dirdate/tmp_patient_snp | uniq  >$dirdate/tmp_snp
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/tmp_result $dirdate/tmp_snp | awk ' BEGIN{OFS=FS="\t"} {$1=null;print $0 }' | sed 's/\t//g' >$dirdate/result_snp
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/patient $dirdate/tmp_snp | cut --complement -f 1 >$dirdate/patient_snp
		#awk -f /home/fuyongsheng1139/refdata/test.awk $dirdate/result_snp $dirdate/patient_snp >$dirdate/final_result
		Rscript /home/fuyongsheng1139/refdata/merge.R $dirdate/patient_snp $dirdate/result_snp $dirdate/vcf_header $dirdate/result/result.txt
		Rscript ref/result.R $dirdate/result/result.txt $dirdate/Polygenic_risk_prediction_results.png
		endtime=$(date +'%Y-%m-%d %H:%M:%S')
		runtime
	else

		awk '$1 ~/^rs/ {print $1}' $dirdate/tmp_result_ukbb | sort | uniq >$dirdate/tmp_result_snp_ukbb
		sort -m $dirdate/snp $dirdate/tmp_result_snp_ukbb $dirdate/tmp_patient_snp | uniq  >$dirdate/tmp_snp_ukbb
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/tmp_result_ukbb $dirdate/tmp_snp_ukbb | awk ' BEGIN{OFS=FS="\t"} {$1=null;print $0 }' | sed 's/\t//g' >$dirdate/result_snp_ukbb
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/patient $dirdate/tmp_snp_ukbb | cut --complement -f 1 >$dirdate/patient_snp_ukbb
		#awk -f /home/fuyongsheng1139/refdata/test.awk $dirdate/result_snp $dirdate/patient_snp >$dirdate/final_result
		Rscript /home/fuyongsheng1139/refdata/merge.R $dirdate/patient_snp_ukbb $dirdate/result_snp_ukbb $dirdate/vcf_header $dirdate/result/result_ukbb.txt
		Rscript ref/result.R $dirdate/result/result_ukbb.txt $dirdate/Polygenic_risk_prediction_results.png

		awk '$1 ~/^rs/ {print $1}' $dirdate/tmp_result_1kg | sort | uniq >$dirdate/tmp_result_snp_1kg
		sort -m $dirdate/snp $dirdate/tmp_result_snp_1kg $dirdate/tmp_patient_snp | uniq  >$dirdate/tmp_snp_1kg
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/tmp_result_1kg $dirdate/tmp_snp_1kg | awk ' BEGIN{OFS=FS="\t"} {$1=null;print $0 }' | sed 's/\t//g' >$dirdate/result_snp_1kg
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/patient $dirdate/tmp_snp_1kg | cut --complement -f 1 >$dirdate/patient_snp_1kg
		#awk -f /home/fuyongsheng1139/refdata/test.awk $dirdate/result_snp $dirdate/patient_snp >$dirdate/final_result
		Rscript /home/fuyongsheng1139/refdata/merge.R $dirdate/patient_snp_1kg $dirdate/result_snp_1kg $dirdate/vcf_header $dirdate/result/result_1kg.txt
		Rscript ref/result.R $dirdate/result/result_1kg.txt $dirdate/Polygenic_risk_prediction_results.png


		endtime=$(date +'%Y-%m-%d %H:%M:%S')
		runtime
	fi
else
	if [[ $length == "1" ]]; then #没有snp，只有一种参考的最简单的情况
		awk '$1 ~/^rs/ {print $1}' $dirdate/tmp_result | sort | uniq >$dirdate/tmp_result_snp
		sort -m $dirdate/tmp_result_snp $dirdate/tmp_patient_snp | uniq  >$dirdate/tmp_snp
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/tmp_result $dirdate/tmp_snp | awk ' BEGIN{OFS=FS="\t"} {$1=null;print $0 }' | sed 's/\t//g' >$dirdate/result_snp
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/patient $dirdate/tmp_snp | cut --complement -f 1 >$dirdate/patient_snp
		#awk -f /home/fuyongsheng1139/refdata/test.awk $dirdate/result_snp $dirdate/patient_snp >$dirdate/final_result
		Rscript /home/fuyongsheng1139/refdata/merge.R $dirdate/patient_snp $dirdate/result_snp $dirdate/vcf_header $dirdate/result/result.txt
		Rscript ref/result.R $dirdate/result/result.txt $dirdate/Polygenic_risk_prediction_results.png
		endtime=$(date +'%Y-%m-%d %H:%M:%S')
		runtime
	else

		awk '$1 ~/^rs/ {print $1}' $dirdate/tmp_result_ukbb | sort | uniq >$dirdate/tmp_result_snp_ukbb
		sort -m $dirdate/tmp_result_snp_ukbb $dirdate/tmp_patient_snp | uniq  >$dirdate/tmp_snp_ukbb
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/tmp_result_ukbb $dirdate/tmp_snp_ukbb | awk ' BEGIN{OFS=FS="\t"} {$1=null;print $0 }' | sed 's/\t//g' >$dirdate/result_snp_ukbb
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/patient $dirdate/tmp_snp_ukbb | cut --complement -f 1 >$dirdate/patient_snp_ukbb
		#awk -f /home/fuyongsheng1139/refdata/test.awk $dirdate/result_snp $dirdate/patient_snp >$dirdate/final_result
		Rscript /home/fuyongsheng1139/refdata/merge.R $dirdate/patient_snp_ukbb $dirdate/result_snp_ukbb $dirdate/vcf_header $dirdate/result/result_ukbb.txt
		Rscript ref/result.R $dirdate/result/result_ukbb.txt $dirdate/Polygenic_risk_prediction_results.png

		awk '$1 ~/^rs/ {print $1}' $dirdate/tmp_result_1kg | sort | uniq >$dirdate/tmp_result_snp_1kg
		sort -m $dirdate/tmp_result_snp_1kg $dirdate/tmp_patient_snp | uniq  >$dirdate/tmp_snp_1kg
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/tmp_result_1kg $dirdate/tmp_snp_1kg | awk ' BEGIN{OFS=FS="\t"} {$1=null;print $0 }' | sed 's/\t//g' >$dirdate/result_snp_1kg
		awk ' BEGIN{OFS=FS="\t"}   NR==FNR{a[$1]=$0;next} NR>=FNR  {if ($1 in a ) {print a[$1]}  }' $dirdate/patient $dirdate/tmp_snp_1kg | cut --complement -f 1 >$dirdate/patient_snp_1kg
		#awk -f /home/fuyongsheng1139/refdata/test.awk $dirdate/result_snp $dirdate/patient_snp >$dirdate/final_result
		Rscript /home/fuyongsheng1139/refdata/merge.R $dirdate/patient_snp_1kg $dirdate/result_snp_1kg $dirdate/vcf_header $dirdate/result/result_1kg.txt
		Rscript ref/result.R $dirdate/result/result_1kg.txt $dirdate/Polygenic_risk_prediction_results.png
		endtime=$(date +'%Y-%m-%d %H:%M:%S')
		runtime

	fi
fi
