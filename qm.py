##################################################################
# The MIT License (MIT)                                          #
#                                                                #
# Copyright (c) 2015 Malte Doentgen                              #
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
## @file	quantummechanics.py
## @author	Felix Schmalz
## @date	2016/01/25
## @brief	methods for controlling the quantum mechanics
#			calculations for simulation.py

import time
import subprocess
#import subprocess32 # said to be more reliable

import log

## @class	QMjobs
## @brief	object that handles gaussian jobs
## @version	2016/01/23:
#		added
class QMjobs:
	## @brief	Constructor
	## @param	DBhandle	database pointer
	## @return	None
	## @version	2016/01/23:
	#		added
	#
	def __init__(self, DBhandle=None):
		# . log
		self.log = log.Log(Width=70)

		# . check DB handle
		if DBhandle == None:
			self.log.printIssue('QMjobs: no database specified!', Fatal=True)
		self.db = DBhandle

		# . list of current processes
		self.joblist = []


	## @brief	start a new QM job
	## @param	Level	accuracy of QM method, medium or high
	## @return	Popen Class of job process
	## @version	2016/01/25:
	#		added
	#
	def startQMjob(self, Input=3, Level='medium'):
		# dummy method

		# subprocess.Popen(args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0)
		# https://docs.python.org/2/library/subprocess.html
		# if too many files open try: close_fds=True
		# set cwd for child working directory

		args = ['sleep', str(Input)]
		
		print 'starting',args[0],args[1]
		
		p = subprocess.Popen(args=args)
		self.joblist.append(p)

		return p


	## @brief	wait for all jobs to end
	## @param	Frequency	checking frequency in s
	## @return
	## @version	2016/01/25:
	#		added
	#
	def collectQMjobs(self, Frequency=2):
		alldone = False
		error = []

		while not alldone:
			print '------'
			tmp = []
			for p in qmjobs.joblist:
				print 'job nr:', p.pid,
				status = p.poll()
				print 'status:',
				if status == None:
					print 'still running ...'
					tmp.append(p)
				else:
					if status >= 0:
						print 'done.'
					else:
						print 'error.'

			if tmp:
				qmjobs.joblist = tmp
				time.sleep(Frequency)
			else:
				alldone = True
			pass



if __name__ == '__main__':

	qmjobs = QMjobs(DBhandle='dummy')

	# test behaviour
	print 'start 10 jobs then check running'
	for i in range(10):
		seconds = 3 + (i-4)**2
		p = qmjobs.startQMjob(Input=seconds)
		print 'job started:', p.pid

	qmjobs.collectQMjobs()
	
	print 'done.'






















