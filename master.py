##################################################################
# The MIT License (MIT)                                          #
#                                                                #
# Copyright (c) 2019 RWTH Aachen University, Malte Doentgen,     #
#                    Felix Schmalz, Leif Kroeger                 #
#                                                                #
# Permission is hereby granted, free of charge, to any person    #
# obtaining a copy of this software and associated documentation #
# files (the "Software"), to deal in the Software without        #
# restriction, including without limitation the rights to use,   #
# copy, modify, merge, publish, distribute, sublicense, and/or   #
# sell copies of the Software, and to permit persons to whom the #
# Software is furnished to do so, subject to the following       #
# conditions:                                                    #
#                                                                #
# The above copyright notice and this permission notice shall be #
# included in all copies or substantial portions of the Software.#
#                                                                #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,#
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES#
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND       #
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,   #
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING   #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR  #
# OTHER DEALINGS IN THE SOFTWARE.                                #
##################################################################
#
## @file	master.py
## @author	Malte Doentgen, Felix Schmalz
## @date	2019/01/18
## @brief	main program
## @version:
#		program intended to bring together analyzing.py and harvesting.py
#		only section that actually writes to the DB
#		analyzing: reac-files with rates etc
#		harvesting: qm-files in qm-folder with frequencies etc
#		both created previously through simulation.py

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
			except: pass
		else: done = True
	reader.close()
	if reaction and (worktime == -1 or worktime < max(reaction)): worktime = max(reaction)
	return worktime, temperature, volume, timestep, reaction

## @brief	read command line input
## @param	argv		command line input
## @return	options		dictionary of {input:value}
## @version	2019/01/18:
#		added support for multiple folders
#
def receiveInput(argv, log=Log.Log(Width=70)):
	# . interpret input
	options = {}
	options['folders'] = []
	i = 0
	while not argv[i].startswith('-'):
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
	if 'reac' not in options: options['reac'] = 'default.reac'
	if 'step' not in options: options['step'] = 0.1
	if 'start' not in options: options['start'] = 0
	if 'end' not in options: options['end'] = -1

	# . defaults: harvesting
	if 'source' not in options: options['source'] = 'QM'
	if 'dbase' not in options: options['dbase'] = 'chemtrayzer.sqlite'
	if 'files' not in options: options['files'] = 'tmp_'
	if 'type' not in options: options['type'] = 'log'
	if 'fail' not in options: options['fail'] = 'keep'
	if 'norm' not in options: options['norm'] = 'keep'

	# . defaults: master
	if 'all' not in options: options['all'] = False
	if 'pressure' not in options: options['pressure'] = 1E5

	return options

#######################################
if __name__ == '__main__':
	log = Log.Log(Width=70)

	###	HEADER
	#
	text = ['sim-folder(s) -dbase <database> [-main <name>] [-step <timestep>] [-start <start>] [-end <end>]',
		'[-source <QM folder>] [-files <filename>] [-type <file extension>] [-fail <behavior on failure>] [-norm <behavior on success>]',
		'[-all <kinetic model size>] [-pressure <pressure/Pa>]',
		'',
		'sim-folder(s):',
		'name of folders where the simulations have run',
		'',
		'analyzing options:',
		'-reac: name of reaction list file produced via processing.py / simulation.py (default="default.reac")',
		'-main: name for output of analyzing.py (default="Default")',
		'-step: give the timestep of the simultaion in [fs] (default=0.1)',
		'-start: skip timesteps smaller than <start> for rate computation (default=0)',
		'-end: end-flag for rate computation (default=-1)',
		'',
		'harvesting options:',
		'-source: name of folder containing the QM results (default="QM")',
		'-dbase: name of the database for reading and writing (default="chemtrayzer.sqlite")',
		'-files: pre-fix for QM files (default="tmp_")',
		'-type: file-extension for QM files (default="log")',
		'-fail: action taken, if harvesting of a file fails. Possible options are: "keep", "delete". (default="keep")',
		'-norm: action taken, if harvesting of a file succeeds. Possible options are: "keep", "delete". (default="keep")',
		'',
		'master options:',
		'-all: if "1", write all database entries to the kinetic model, elif "0", only for species and reactions observed during trajectory simulation (default="0")',
		'-pressure: specifiy pressure for computing the translational partition function, in [Pa] (default=1E5)',
		'']
	log.printHead(Title='ChemTraYzer 2 - Chemical Trajectory Analyzer', Version='2019-01-18', Author='Malte Doentgen, LTT RWTH Aachen University', Email='chemtrayzer@ltt.rwth-aachen.de', Text='\n\n'.join(text))

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
	options = receiveInput(argv, log=log)
	if not options['folders']:
		log.printIssue(Text='No simulation folder supplied, cannot continue', Fatal=True)
	elif not options['source']:
		log.printIssue(Text='No source folder supplied, cannot process QM data', Fatal=True)
	elif not options['dbase']:
		log.printIssue(Text='No database supplied, cannot store trajectory or QM data', Fatal=True)
	db = dbhandler.Database(Name=options['dbase'],Timeout=10)

	###	READ TRAJECTORY FILES
	#
	reaction = {}
	log.printComment(Text='The reaction files (*.reac) of the following work folders will be merged into a single list of reactions. All virtual reactions required for initial molecule creation are stored at time=0 !', onlyBody=False)
	log.printBody(Text=', '.join(os.path.join(f,options['reac']) for f in options['folders']), Indent=1)
	log.printBody(Text='', Indent=1)
	tshift = 0.0
	for f in options['folders']:
		filename = os.path.join(f,options['reac'])
		wt, T, V, dt, tmp = readWork(filename)
		for time in tmp:
			if time+tshift in reaction: reaction[time+tshift] += tmp[time]
			else: reaction[time+tshift] = tmp[time]
		tshift = max(reaction)
		log.printBody(Text='timesteps '+repr(min(tmp))+' to '+repr(wt)+' read from "'+filename+'"', Indent=1)
	log.printBody(Text='', Indent=1)

	if T == -1 or V == -1 or dt == -1: log.printIssue(Text='Extracted simulation parameters faulty.', Fatal=True)

	###	REACTION ANALYSIS
	#
	anly = analyzing.Analyzing(Reaction=reaction, Main=options['main'], Start=options['start'], End=options['end'], Vol=V, Timestep=dt)
	anly.writeData()

	###	QUANTUM ANALYSIS
	#
	# . loop folders and harvest
	blessdict = {}
	harv = harvesting.Harvesting(DBhandle=db)
	# . test DB on reference species (they may not be there)
	#   it's user responsability, if they are missing (produces wrong NASA polynomials)
	harv.getHa0()
	for f in options['folders']:
		qmfolder = os.path.join(f,options['source'])
		log.printComment('harvest in %s' %(qmfolder))
		done, failed, total, barrierless = harv.harvestFolder(Folder=qmfolder, Files=options['files'], Type=options['type'], Fail=options['fail'], Done=options['norm'])
		blessdict[f] = barrierless
		log.printComment('%d of %d results written to database, %d failures' %(done, total, failed))

	# . set up species list
	species_DB = db.getSpecies()
	if options['all']: species = species_DB
	else: species = [spec for spec in anly.species if spec in species_DB]
	# . fit NASA polynomials for all species
	log.printBody(Text='Fitting NASA parameters ...', Indent=1)
	[harv.fitNASA(Smi=spec, Pressure=options['pressure'], T1=300.0, T2=1000.0, T3=3000.0, dT=10.0) for spec in species]
	harv.writeNASA(Filename=options['main']+'.therm')
	log.printBody(Text='... NASA parameters done', Indent=1)

	###	BARRIERLESS REACTIONS
	#
	# . merge barrierless reactions
	#   ruled out by simulation.py (reac.list.b)
	#   with those ruled out by harvesting.py
	for f in options['folders']:
		barrierless = blessdict[f]
		barrierlesspath = os.path.join(f,'reac.dat/reac.list.b')
		if os.path.exists(barrierlesspath):
			barrierlessfile = open(barrierlesspath, 'r')
			for line in barrierlessfile:
				try:
					s = line.strip().split()
					reacA = s[0].split(':')[0].split(',')
					reacB = s[0].split(':')[1].split(',')
					if len(reacA) > len(reacB): smile = s[0]
					else: smile = ','.join(reacB)+':'+','.join(reacA)
					barrierless[smile] = s[1]
				except: log.printIssue(Text='Extracted barrierless data faulty.', Fatal=False)
			barrierlessfile.close()

		# . update DB with barrierless reactions
		#   store added reactions in extra file
		barrierlessdone = {}; barrierlessdonefile = {}
		barrierlessdonepath = os.path.join(f,'reac.dat/reac.list.b.done')
		# . get already added barrierless reactions
		#   to only add them once per simulation replica
		if os.path.exists(barrierlessdonepath): barrierlessdonefile = open(barrierlessdonepath, 'r')
		for line in barrierlessdonefile:
			try: smi = line.strip(); barrierlessdone[smi] = True;
			except: pass

		# . update DB
		#   no reactions where reactants=products
		for smile in barrierless:
			reacA = smile.split(':')[0]
			reacB = smile.split(':')[1]
			if smile not in barrierlessdone and sorted(reacA.split(',')) != sorted(reacB.split(',')) and smile in anly.rate:
				rate, n  = anly.rate[smile]
				klo, kup = anly.err[smile]
				# . calculate missing association rate constants via equilibrium constant
				if rate == 0.0 and all(smi in harv.NASA for smi in reacA.split(',')+reacB.split(',')):	# only dissociation ReaxFF rate constant available
					dG = 0.0
					for smi in reacA.split(','):
						if T > harv.NASA[smi][2][1]: p = harv.NASA[smi][0][0:7]
						else: p = harv.NASA[smi][0][7:14]
						dG -= harv.nasaGRT(T, p[0], p[1], p[2], p[3], p[4], p[5], p[6])
					for smi in reacB.split(','):
						if T > harv.NASA[smi][2][1]: p = harv.NASA[smi][0][0:7]
						else: p = harv.NASA[smi][0][7:14]
						dG += harv.nasaGRT(T, p[0], p[1], p[2], p[3], p[4], p[5], p[6])
					Keq = numpy.exp(-dG) # k(association)/k(dissociation)
					rate = Keq*anly.rate[reacB+':'+reacA][0]
					n = 0
				m = barrierless[smile]
				db.addReactionB(Smile=smile, M=m, FFrate=rate, Temperature=T, Klo=klo, Kup=kup, N=n)
				barrierlessdone[smile] = True
		if os.path.exists(barrierlessdonepath): barrierlessdonefile.close()
		# . write updated list of added barrierless reactions
		barrierlessdonefile = open(barrierlessdonepath, 'w')
		for smile in barrierlessdone:
			barrierlessdonefile.write('%s\n' %smile)
		barrierlessdonefile.close()

	###	MECHANISM
	#
	reactions_DB = db.getTSReactions() + db.getBarrierlessReactions()
	# . whole DB or only the specified simulations?
	if options['all']:
		species = species_DB
		barrierlessreactions = db.getBarrierlessReactions()
		reactions = reactions_DB
	else:
		species = [spec for spec in anly.species if spec in species_DB]
		barrierlessreactions = list(set( [smile for f in options['folders'] for smile in blessdict[f]] ))
		reactions = []
		for smile in sorted(anly.reaction):
			reactants = smile.split(':')[0].split(',')
			products  = smile.split(':')[1].split(',')
			# . are all reactants and products of reaction available?
			allSpeciesInDB = all(reactant in species_DB for reactant in reactants) and  all(product in species_DB for product in products)
			if smile in reactions_DB and allSpeciesInDB:
				reactions.append(smile)
				
	# . fit Arrhenius rates for all reactions
	log.printBody(Text='Fitting Arrhenius parameters ...', Indent=1)
	for smile in reactions:
		if smile in barrierlessreactions: harv.fitBarrierless(Reac=smile)
		else: harv.fitArr(Reac=smile, T1=300.0, T3=3000.0, dT=10.0)
	harv.writeArr(Filename=options['main']+'.chem')
	log.printBody(Text='... Arrhenius parameters done', Indent=1)


