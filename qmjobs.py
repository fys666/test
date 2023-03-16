

import sys
import os
import numpy

import harvesting
import analyzing
import dbhandler
import log as Log


## @brief	read the trajectory file from the MD simulation
## @param	Work		Filename
## @return	worktime	biggest timestep
## @return	temperature	temp. of simulation
## @return	reaction	ocurred reactions
## @version	2016/02/24:
#		copied here from analyzing.py
#
def readWork(Work):
	reader = open(Work, 'r')
	done = False
	worktime = -1
	temperature = -1
	volume = -1
	timestep = -1
	thermaltime = -1
	reaction = {}
	while not done:
		line = reader.readline().strip()
		words = line.split(':')
		if 'ON THE FLY' in line:
			try: temperature = float(line.split()[4])
			except: pass
			try: volume = float(line.split()[5])
			except: pass
			try: timestep = float(line.split()[6])
			except: pass
		try: int(words[0])
		except:
			if len(words) == 1 and words[0] == '': done = True
			continue
		if len(words) > 1:
			try:
				int(words[0])
				if int(words[0]) not in reaction:
					reaction[int(words[0])] = [[words[1].split('\n')[0].split(','), words[2].split('\n')[0].split(',')]]
				else:
					reaction[int(words[0])].append([words[1].split('\n')[0].split(','), words[2].split('\n')[0].split(',')])
				if thermaltime < 0 and int(words[0]) > 0: thermaltime = int(words[0])
			except: pass
		else: done = True
	reader.close()
	if reaction and (worktime == -1 or worktime < max(reaction)): worktime = max(reaction)
	return worktime, temperature, volume, timestep, thermaltime, reaction

def receiveInput(argv, log=Log.Log(Width=70)):
	# . interpret input
	options = {}
	options['folders'] = []
	i = 0
	while i < len(argv) and not argv[i].startswith('-'):
		options['folders'].append(argv[i])
		i += 1
	while i < len(argv)-1:
		arg = argv[i]
		opt = argv[i+1]
		if arg.startswith('-'):
			if opt.startswith('-'): log.printIssue(Text='Missing value for option "%s". Will be ignored.' %arg, Fatal=False)
			else:
				try: tmp = float(opt)
				except: tmp = opt
				options[arg[1:].lower()] = tmp
				i += 1
		i += 1

	# . defaults: analyzing
	if 'main' not in options: options['main'] = 'Default'
	#if 'step' not in options: options['step'] = 0.1
	if 'start' not in options: options['start'] = 0
	if 'end' not in options: options['end'] = -1
	if 'reac' not in options: options['reac'] = 'default.reac'

	# . defaults: harvesting
	if 'source' not in options: options['source'] = 'QM'
	if 'dbase' not in options: options['dbase'] = 'qmjobs.sqlite'
	if 'files' not in options: options['files'] = 'tmp_'
	if 'type' not in options: options['type'] = 'log'
	#if 'fail' not in options: options['fail'] = 'keep'
	#if 'norm' not in options: options['norm'] = 'keep'

	# . defaults: master
	if 'all' not in options: options['all'] = False
	if 'pressure' not in options: options['pressure'] = 1E5
	if 'thermalize' not in options: options['thermalize'] = 1E6

	return options

#######################################
if __name__ == '__main__':
	log = Log.Log(Width=70)

	###	HEADER
	#
	#text = ['<simulation folder> [<more simulation folders>] [-main <main>] [-step <timestep>] [-start <start>] [-end <end>]',
	#	'-source <QM folder> -dbase <database> [-files <filename>] [-type <file extension>] [-fail <behavior on failure>] [-norm <behavior on success>]',
	#	'[-all <kinetic model size>] [-pressure <pressure/Pa>] [-thermalize <time to thermalize/fs>]',
	#	'',
	#	'analyzing options:',
	#	'-reac: name of .reac file produced via processing.py / simulation.py',
	#	'-main: name for output of analyzing.py (default="Default")',
	#	'-step: give the timestep of the simultaion in [fs] (default=0.1)',
	#	'-start: skip timesteps smaller than <start> for rate computation (default=0)',
	#	'-end: end-flag for rate computation (default=-1)',
	#	'',
	#	'harvesting options:',
	#	'-source: name of folder containing the QM results (default="QM")',
	#	'-dbase: name of the database for reading and writing (default="chemtrayzer.sqlite")',
	#	'-files: pre-fix for QM files (default="tmp_")',
	#	'-type: file-extension for QM files (default="log")',
	#	'-fail: action taken, if harvesting of a file fails. Possible options are: "keep", "delete". (default="keep")',
	#	'-norm: action taken, if harvesting of a file succeeds. Possible options are: "keep", "delete". (default="keep")',
	#	'',
	#	'master options:',
	#	'-all: if "1", write all database entries to the kinetic model, elif "0", only for species and reactions observed during trajectory simulation (default="0")',
	#	'-pressure: specifiy pressure for computing the translational partition function, in [Pa] (default=1E5)',
	#	'-thermalize: exclude trajectories with events before this time, in [fs] (default=1E6)',
	#	'',
	#	'examples:',
	#	'python qmjobs.py CH4.1600K.* -dbase chemtrayzer.sqlite -files retry_ -main Master3 -all 1'
	#	'python ../bin/qmjobs.py Run1 Run2 Run3 Run4 Run5 Run6 Run7 Run8 Run9 Run10 -dbase ../chemtrayzer.sqlite -files "" -thermalize 0'
	#	'']
	#log.printHead(Title='ChemTraYzer - Chemical Trajectory Analyzer', Version='2016-09-01', Author='Malte Doentgen, LTT RWTH Aachen University', Email='chemtrayzer@ltt.rwth-aachen.de', Text='\n\n'.join(text))

	###	INTERPRET INPUT
	#
	if len(sys.argv) > 1: argv = sys.argv[1:]
	else:
		log.printComment(Text=' Use keyboard to type in commands. Use <strg>+<c> or write "done" to proceed.', onlyBody=False)
		argv = []; done = False
		while not done:
			try: tmp = raw_input('')
			except: done = True
			if 'done' in tmp.lower(): done = True
			else:
				if '!' in tmp: argv += tmp[:tmp.index('!')].split()
				else: argv += tmp.split()
	#print argv
	options = receiveInput(argv, log=log)
	if not options['folders']:
		log.printIssue(Text='No folder names supplied, cannot find simulation data', Fatal=True)


	###	READ TRAJECTORY FILES
	#
	reaction = {} # time resolved
	event = {} # event resolved
	tshift = 0.0
	excluded_reac = []; combined_reac = []
	wt, T, V, dt, tt, tmp = -1,-1,-1,-1,-1,{}
	for f in options['folders']:
		reacfile = os.path.join(f,options['reac'])
		if os.path.exists(reacfile):
			wt, T, V, dt, tt, tmp = readWork(reacfile)
			if tt*dt > float(options['thermalize']): # 1 ns thermalize
				for time in tmp:
					if time+tshift in reaction: reaction[time+tshift] += tmp[time]
					else: reaction[time+tshift] = tmp[time]
				tshift = max(reaction)
				#log.printBody(Text='timesteps '+repr(min(tmp))+' to '+repr(wt)+' read from "'+reacfile+'"', Indent=1)
				combined_reac.append(reacfile)
			else:
				#log.printBody(Text='thermalization criterion not met in "'+reacfile+'"', Indent=1)
				excluded_reac.append(reacfile)
		else:
			#log.printBody(Text='no such file "'+reacfile+'"', Indent=1)
			pass
	log.printComment(Text='The following list of work files were merged into a single list of reactions.', onlyBody=False)
	log.printBody(Text=', '.join(combined_reac), Indent=1)
	log.printComment(Text='The following list of work files were excluded.', onlyBody=False)
	log.printBody(Text=', '.join(excluded_reac), Indent=1)
	log.printBody(Text='', Indent=1)
	log.printBody(Text='', Indent=1)
	if T == -1 or V == -1 or dt == -1: log.printIssue(Text='Extracted simulation parameters faulty.', Fatal=True)

	###	WRITE JOINED TRAJECTORY FILE
	#
	joined_reac = open(options['main']+'.'+options['reac'], 'w')
	joined_reac.write('ON THE FLY ... %.1f %.1f %.1f\n' %(T,V,dt))
	for time in sorted(reaction):
		#reaction[time] = [[ [reac] , [prod] ], ... ]
		#tmp = reaction[time]
		for mols in reaction[time]:
			#mols = [ [reac] , [prod] ]
			#print mols
			#print '%d:%s:%s' %(int(time), ','.join(mols[0]), ','.join(mols[1]))
			joined_reac.write('%d:%s:%s\n' %(int(time), ','.join(mols[0]), ','.join(mols[1])))
			# "events" = reaction, reactants, products, no fakes
			if not [''] in mols:
				rsmi = '%s:%s' %(','.join(sorted(mols[0])), ','.join(sorted(mols[1]))) ## TODO: sort in simulation.py when writing to default.reac
				try: event[rsmi].append(time)
				except KeyError: event[rsmi] = [time]
			for smi in mols[0]+mols[1]:
				if smi:
					try: event[smi].append(time)
					except KeyError: event[smi] = [time]
	joined_reac.close()

	####	QUANTUM ANALYSIS aka READ QM FILES --> todo: put in harv.harvestfolderS
	#
	jobs = {}
	qmfail = {}
	eventfail = {}
	barrierless = {}
	db = dbhandler.Database(Name=options['dbase'])
	harv = harvesting.Harvesting(DBhandle=db)
	## jobs[] = total, qmfail = fail, barrierless = barrierless
	# jobs, barrierless, qmfail = harv.harvestfolderS(Folders=options['folders'], QM=options['source'], Files=options['files'], Type=options['type'])
	datafiles = []
	for f in options['folders']:
		qmfolder = os.path.join(f,options['source'])
		# . create list of files
		if not os.path.exists(qmfolder):
			#log.printIssue('No folder named %s.' %(qmfolder))
			pass
		else:
			noFiles = True
			for file in os.listdir(qmfolder):
				if file.startswith(options['files']) and file.endswith(options['type']):
					datafiles.append(os.path.join(qmfolder,file)); noFiles = False
			if noFiles: log.printIssue('No files found in "%s" matching "%s*%s"' %(qmfolder,options['files'],options['type']))
	#print 'Reading QM data from %d g09 log files.' %(len(datafiles))
	log.printBody(Text='Reading QM data from %d g09 log files.'%(len(datafiles)))
	for file in datafiles:
		#print file
		filename = file.split('/')[-1]
		#sim      = file.split('/')[-3]
		#folder   = file[:-len(options['source']-len(filename)-1]
		molinfo = harv.harvestGaussian(file)
		#print 'molinfo found:'
		#print molinfo
		smi   = molinfo['smi']
		#v0    = molinfo['v0']
		#M     = molinfo['M']
		#Ip    = molinfo['Ip']
		#cSPE  = molinfo['cSPE']
		normalTerm = molinfo['normalTerm']
		confirmed  = molinfo['confirmed']
		#jobinfo = [normalTerm,confirmed,sim,filename]
		jobinfo = [molinfo,file,filename,-1]
		try:             jobs[smi].append(jobinfo)
		except KeyError: jobs[smi] = [jobinfo]

		if not smi: qmfail[file] = 'smiles identifier missing'; continue
		if not normalTerm: qmfail[file] = 'g09 error @ link %s' %(molinfo['errorLink']); continue
		if not molinfo['M'] or not molinfo['Ip'] or not molinfo['cSPE']:
			qmfail[file] = 'molecular information missing'; continue
		if not confirmed:  qmfail[file] = 'IRC check did not confirm TS or molecule broke during optimization'; continue

		if ':' in smi:
			# reaction
			cmd = molinfo['cmd'][0]
			#cmd = molinfo['cmd'][1] if len(molinfo['cmd']) > 1 else '?'
			methodok = db.verifyMethod(cmd,TS=True)
			if not methodok: qmfail[file] = 'qm method %s not compatible' %(cmd); continue
			if all([v > 0 for v in molinfo['v0']]):
				# . barrierless reaction
				barrierless[smi] = molinfo['M']
			elif methodok and normalTerm and confirmed:
				# . all ok
				#   add and report result
				conformer = db.addReaction(Molinfo=molinfo,RetConf=True)
				jobs[smi][-1][3] = conformer
		else:
			# species
			methodok = db.verifyMethod(molinfo['cmd'][0],TS=False)
			if not methodok: qmfail[file] = 'qm method %s not compatible' %(molinfo['cmd'][0]); continue
			if methodok and normalTerm and confirmed:
				# . all ok
				#   add and report result
				conformer = db.addSpecies(Molinfo=molinfo,RetConf=True)
				jobs[smi][-1][3] = conformer
		## retry
		## failure
		## delete or keep ? <- always keep

	reactions_db = db.getTSReactions()
	species_db = db.getSpecies()
	#print 'found %d species and %d transition states in DB' %(len(reactions_db),len(species_db))



	####	REACTION ANALYSIS <-- trajectory reactions
	##
	anly = analyzing.Analyzing(Reaction=reaction, Main=options['main'], Start=options['start'], End=options['end'], Vol=V, Timestep=dt)
	anly.writeData()


	####	Fit NASA polynomials
	#
	## . test DB on reference species (they may not be there)
	##   it's user responsability, if they are missing (produces wrong NASA polynomials)
	harv.getHa0()
	if options['all']: species = species_db
	else: species = [spec for spec in anly.species if spec in species_db]
	#print 'dev: species:', species
	# . fit NASA polynomials for all species
        log.printBody(Text='Fitting NASA parameters ...', Indent=1)
	[harv.fitNASA(Smi=spec, Pressure=options['pressure'], T1=300.0, T2=1000.0, T3=3000.0, dT=10.0) for spec in species]
	harv.writeNASA(Filename=options['main']+'.therm')
        log.printBody(Text='... NASA parameters done', Indent=1)


	###	BARRIERLESS REACTIONS <-- merge
	#
	##barrierless = {}
	barrierlessdone = {}
	for f in options['folders']:
		filename = os.path.join(f,'reac.dat/reac.list.b')
		if os.path.exists(filename+'.done'):
			bdonefile = open(filename+'.done', 'r')
			for line in bdonefile:
				try: smi = line.strip(); barrierlessdone[smi] = True;
				except: pass
			bdonefile.close()
		if os.path.exists(filename):
			bfile = open(filename, 'r')
			for line in bfile:
				try:
					s = line.strip().split()
					reacA = s[0].split(':')[0].split(',')
					reacB = s[0].split(':')[1].split(',')
					if len(reacA) > len(reacB): smi = s[0]
					else: smi = ','.join(reacB)+':'+','.join(reacA)
					barrierless[smi] = s[1]
				except: log.printIssue(Text='Extracted barrierless data faulty.', Fatal=False)
			bfile.close()

	###	BARRIERLESS REACTIONS <-- add, analyzing
	#
	## . update DB with barrierless reactions
	#   store added reactions in extra file
	#barrierlessdone = {}; barrierlessdonefile = {}
	# . get already added barrierless reactions
	#if os.path.exists('reac.dat/reac.list.b.done'): barrierlessdonefile = open('reac.dat/reac.list.b.done', 'r')
	#for line in barrierlessdonefile:
	#	try: smi = line.strip(); barrierlessdone[smi] = True;
	#	except: pass
	# . update DB
	#   no reactions where reactants=products
	for reac in barrierless:
		reacA = reac.split(':')[0].split(',')
		reacB = reac.split(':')[1].split(',')
		if reac not in barrierlessdone and sorted(reacA) != sorted(reacB) and reac in anly.rate:
			rate, n  = anly.rate[reac]
			klo, kup = anly.err[reac]
			# . calculate missing association rate constants via equilibrium constant
			if rate == 0.0:	# only dissociation ReaxFF rate constant available
				if not all(smi in harv.NASA for smi in reacA+reacB):
					log.printIssue(Text='Barrierless reaction "%s" has rate==0.0 and a reactant is missing in in NASA polynomials.' %(reac), Fatal=False)
					continue
				dG = 0.0
				for smi in reacA:
					if T > harv.NASA[smi][2][1]: p = harv.NASA[smi][0][0:7]
					else: p = harv.NASA[smi][0][7:14]
					dG -= harv.nasaGRT(T, p[0], p[1], p[2], p[3], p[4], p[5], p[6])
				for smi in reacB:
					if T > harv.NASA[smi][2][1]: p = harv.NASA[smi][0][0:7]
					else: p = harv.NASA[smi][0][7:14]
					dG += harv.nasaGRT(T, p[0], p[1], p[2], p[3], p[4], p[5], p[6])
				Keq = numpy.exp(-dG) # k(association)/k(dissociation)
				rate = Keq*anly.rate[','.join(reacB)+':'+','.join(reacA)][0]
				n = 0
			m = barrierless[reac]
			db.addReactionB(Smile=reac, M=m, FFrate=rate, Temperature=T, Klo=klo, Kup=kup, N=n)
			barrierlessdone[reac] = True
	#if os.path.exists('reac.dat/reac.list.b.done'): barrierlessdonefile.close()
	# . write updated list of added barrierless reactions
	#barrierlessdonefile = open('reac.dat/reac.list.b.done', 'w')
	#for reac in barrierlessdone:
	#	barrierlessdonefile.write('%s\n' %reac)
	#barrierlessdonefile.close()
	for f in options['folders']:
		filename = os.path.join(f,'reac.dat/reac.list.b')
		if os.path.exists(filename):
			bdonefile = open(filename+'.done', 'w')
			for reac in barrierlessdone:
				bdonefile.write('%s\n' %reac)
			bdonefile.close()


	barrierless_db = db.getBarrierlessReactions()
	#print 'found %d barrierless reactions in DB:' %(len(barrierless_db))
	#for reac in barrierless_db:
	#	print ' %25s ' %(reac)
	

	###	List events and success
	#
	print 'SMILES ID | in DB | Jobs tot./succ./conf. | sym cSPE #v0 #rotor'
	for smi in event:
		revsmi = ':'.join(smi.split(':')[::-1])
		# . check DB lists for smiles id
		isB     = smi    in barrierless_db
		revIsB  = revsmi in barrierless_db
		inDB    = smi    in species_db or smi in reactions_db or isB
		revInDB = revsmi in reactions_db or revIsB
		# . try to get data from DB
		if isB or revIsB:
			if isB:       conf = zip(*db.getBarrierlessData(Reac=smi))
			elif revIsB:  conf = zip(*db.getBarrierlessData(Reac=revsmi))
			else:         conf = []
		else:
			if inDB:      conf = db.getConf(Smi=smi)
			elif revInDB: conf = db.getConf(Smi=revsmi)
			else:         conf = []
		isB = isB or revIsB
		inDB = inDB or revInDB
		if not inDB: eventfail[smi] = []
		# . look for job data
		joblist = []
		try: joblist = jobs[smi]
		except KeyError:
			if ':' in smi:
				try: joblist = jobs[revsmi]
				except KeyError: pass
		jobCount = {}
		if len(joblist) > 0:
			for jobinfo in joblist:
				# . jobinfo: [molinfo,file,filename,conformer]
				#   add filename to fail list
				if not inDB: eventfail[smi].append(jobinfo[1])
				# . resulting conformer
				c = jobinfo[3]
				try: jobCount[c]
				except KeyError: jobCount[c] = [0,0,0]
				jobCount[c][0] += 1
				# . job success
				if jobinfo[0]['normalTerm']:
					jobCount[c][1] += 1
					if jobinfo[0]['confirmed']:
						jobCount[c][2] += 1

		#print '%10s | ' %smi
		#print '%s | (%3d/%3d/%3d) | %2d | %s' %('X' if inDB else ' ', confirmed, normalTerm, numJobs, numConf, molData)
		
		#if numConf > 1:
		#c = 0
		#for prop in conf:
		#	c = prop['conformer']
		#	#molData = prop{'M':0.0, 'cSPE':0.0, 'Tr':[], 'sym':0, 'v0':[], 'rotor':{}, 'spin':0, , 'Htherm':0.0, }
		#	molData = '%2d %5.1f %2d %2d' %(prop['sym'],prop['cSPE'],len(prop['v0']),len(prop['rotor']))
		#	print '%10s | %s | %2d' %(smi, 'X' if inDB else ' ', c) ,
		#	if c in numJobs:
		#		print ' | (%3d/%3d/%3d)' %(confirmed[c], normalTerm[c], numJobs[c])	
		#	else:
		#		print ' | (   /   /   )'
		#	print ' | %s' %moldata
		
		#cDB = [prop['conformer'] for prop in conf]
		#for c in jobCount:
		#	#print '%25s | %s | %2d | (%3d/%3d/%3d)' %(smi, 'X' if inDB else ' ', c, confirmed[c], normalTerm[c], numJobs[c]) ,
		#	print '%25s | %s | %2s | (%3d/%3d/%3d) | ' %(smi, 'X' if inDB else ' ', c if c>-1 else ' ', jobCount[c][0], jobCount[c][1], jobCount[c][2]) ,
		#	if c in cDB:
		#		prop = conf[cDB.index(c)]
		#		print '%2d %6.1f %2d %2d' %(prop['sym'],prop['cSPE'],len(prop['v0']),len(prop['rotor'])) ,
		#	print
		
		# . print out events + conformer + DB status
		print ' %24s | %s |%4d%4d%4d | ' %(smi, 'X' if inDB else '-', sum(jobCount[c][0] for c in jobCount), sum(jobCount[c][1] for c in jobCount), sum(jobCount[c][2] for c in jobCount)) , 
		if len(conf) == 0: # keine daten
			print
		elif len(conf) == 1: # keine conformere / nur eine temperatur # [t,k,klo,kup,n]
			if isB: print '%e %3d'            %(conf[0][1],conf[0][4])
			else:   print '%2d %6.1f %2d %2d' %(conf[0]['sym'],conf[0]['cSPE'],len(conf[0]['v0']),len(conf[0]['rotor']))
		else:
			print
			for prop in conf: # DB liste durchgehen
				if isB:
					print '%24.1f  | %s |             | %e %3d'            %(prop[0], 'X', prop[1], prop[4])
				else:
					c = prop['conformer']
					if c in jobCount: # bei jobs dabei?
						print '%24d  | %s |%4d%4d%4d | ' %(c, 'X', jobCount[c][0], jobCount[c][1], jobCount[c][2]) ,
					else:
						print '%24d  | %s |             | ' %(c, 'X') ,
					print '%2d %6.1f %2d %2d' %(prop['sym'],prop['cSPE'],len(prop['v0']),len(prop['rotor']))

	
	###	FAILS + reason
	#
	print 'FAILED Smiles ID | reason'
	for smi in eventfail:
		print '%25s' %(smi)
		for file in eventfail[smi]:
			try: reason = qmfail[file]
			except KeyError: reason = 'unknown'
			filename = file.split('/')[-1]
			folder = file.split('/')[-3]
			if len(folder)>25: folder = folder[len(folder)-25:]
			print ' %25s | %25s | %25s' %(folder, filename, reason)


	###	MECHANISM <-- reactions, barrierless
	#
	reactions_db = barrierless_db + reactions_db
	if options['all']:
		species = species_db
		barrierless = barrierless_db
		reactions = reactions_db
	else:
		species = [spec for spec in anly.species if spec in species_db]
		reactions = []
		for reac in sorted(anly.reaction):
			reactants = reac.split(':')[0].split(',')
			products  = reac.split(':')[1].split(',')
			allSpeciesInDB = all(reactant in species_db for reactant in reactants) and all(product in species_db for product in products)
			if reac in reactions_db and allSpeciesInDB: # and reac not in reactions
				reactions.append(reac)

	# . fit Arrhenius rates for all reactions
        log.printBody(Text='Fitting Arrhenius parameters ...', Indent=1)
	for reac in reactions:
		if reac in barrierless: harv.fitBarrierless(Reac=reac)
		else: harv.fitArr(Reac=reac, T1=300.0, T3=3000.0, dT=10.0)
	harv.writeArr(Filename=options['main']+'.chem')
        log.printBody(Text='... Arrhenius parameters done', Indent=1)


