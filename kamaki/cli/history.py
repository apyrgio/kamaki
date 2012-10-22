#!/usr/bin/env python

# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from os.path import exists

def order_free_contains(containing, contained):
	superset = containing.split()
	for term in contained.split():
		if term not in superset:
			return False
	return True

class History(object):
	def __init__(self, filepath):
		self.filepath=filepath

	@classmethod
	def _match(self,line, match_terms):
		if match_terms is None:
			return True
		for term in match_terms.split():
			if term not in line:
				return False
		return True

	def get(self, match_terms=None, limit=0):
		f = open(self.filepath, 'r')
		result = ['%s.  \t%s'%(index+1,line) \
			for index,line in enumerate(f.readlines()) \
			if self._match(line, match_terms)]
		offset = len(result)-limit if limit and len(result) > limit else 0
		return result[offset:]

	def add(self, line):
		f = open(self.filepath, 'a+')
		f.write(line+'\n')
		f.close()

	def clean(self):
		f = open(self.filepath, 'w')
		f.close()