
import csv

class Passive:
	'''
	represents a passive electrical component
	'''
	
	def __init__(self, value = 0, tolerance = 0, type = ''):
		self.value = value
		self.tolerance = tolerance
		self.type = type
		
	def __str__(self):
		pretty_string = self.type + ": " + str(self.value) + ", tol = " + str(self.tolerance)
		return pretty_string
#end class Passive
		
class PassiveNetwork:
	'''
	represents a passive network fulfilling some criteria
	
	self.impedance is intended impedance of network
	self.error is the % error of the network from the intended impedance
	self.type is the type of network
	self.components is a list of components used in the network
		- components are listed in an order corresponding to self.type
	'''
	network_types = ['series', 'parallel']
	
	def __init__(self, type, goal, impedance = 0, error = 0, tolerance = 0):
		self.impedance = impedance # the intended impedance of the passive network
		self.goal = goal
		self.error = error
		self.type = type #TODO: add error checking for type
		self.components = [] #interpreted based on self.type (always in numerical order)
		
	def __str__(self):
		pretty_string = "impedance: " + str(self.impedance)
		if self.type == 'series':
			pretty_string += "\nVhi---P1---P2---Vlo"
		elif self.type == 'parallel':
			pretty_string += "\n    Vhi\n     |\n   ----\n   |  |\n  P1  P2\n   |  |\n   ----\n     |\n    Vlo"
		pretty_string += "\n\tgoal: " + str(self.goal) + ", error: " + str(self.error)
		for i in self.components:
			pretty_string += "\n\tcomponents: " + str(i)
		return pretty_string
#end class PassiveNetwork

class PassiveSolver:
	'''
	A solver to simplify the creation of purely resistive, capacitive,
	or inductive circuits.
	'''
	
	### set up necessary lists	
	def __init__(self):
		self.res = []
		self.cap = []
		self.ind = []
	
	def add_resistor_list(self, res_list_file="E96_resistor_values.csv"):
		'''
		load up lists for resistor values
		csvs are assumed to have value in first column, tolerance in second
		'''
		reader = open(res_list_file,"rb")
		
		for line in reader:
			li=line.strip()
			if not li.startswith("#"):
				p = [float(x) for x in li.split(',')]
				self.res.append(Passive(p[0], p[1], 'r'))

	def add_capacitor_list(self, cap_list_file="RF_caps_20141109.csv"):
		'''
		load up lists for capacitor values
		csvs are assumed to have value in first column, tolerance in second
		'''
		reader = open(cap_list_file,"rb")
		
		for line in reader:
			li=line.strip()
			if not li.startswith("#"):
				li.strip()
				p = [float(x) for x in li.split(',')]
				self.cap.append(Passive(p[0], p[1], 'c'))
				
	def add_inductor_list(self, ind_list_file="RF_ind_20141109.csv"):
		'''
		load up lists for inductor values
		csvs are assumed to have value in first column, tolerance in second
		'''
		reader = open(ind_list_file,"rb")
		
		for line in reader:
			li=line.strip()
			if not li.startswith("#"):
				p = [float(x) for x in li.split(',')]
				self.ind.append(Passive(p[0], p[1], 'l'))
				
	### helper functions
	def binary_search_value(self, goal, components):
		'''
		do a binary search on the list of components
		each element of components is a list of component details
		the first element of components is the value
		
		returns [closest_component, index_of_component]
		'''
		# if there's only one element of the list, it's definitely the closest
		if (len(components) == 1):
			return components[0]
		
		# just get half the list that contains the closest value
		half = len(components)/2
		if (goal == components[half].value):
			# early stopping if we find one that's the exact value
			return components[half]
		elif (goal < components[half].value):
			# we should look in the bottom half of the list
			return self.binary_search_value(goal, components[:half])
		else:
			# we should look in the top half of the list
			return self.binary_search_value(goal, components[half:])
	
	def add_components(self, comp_a, comp_b):
		mag = comp_a.value+comp_b.value
		# note that this assumes uncorrelated tolerances errors on the parts
		# that's unlikely to be the case if the parts are from the same batch
		tol = abs(comp_a.value * comp_a.tolerance + comp_b.value * comp_b.tolerance)/mag
		return Passive(mag, tol)
		
	def piggyback_components(self, comp_a, comp_b):
		mag = 1/(1/comp_a.value + 1/comp_b.value)
		tol = (1/(1/(comp_a.value + comp_a.tolerance) + 1/comp_b.value + comp_b.tolerance))/mag
		return Passive(mag, tol)
	
	### Functions to find closest resistor value
	def find_closest_r(self, goal):
		closest = self.binary_search_value(goal, self.res)
		#closest.append(abs(closest.value-goal)/goal)
		return closest
		
	def find_closest_c(self, goal):
		closest = self.binary_search_value(goal, self.cap)
		#closest.append(abs(closest.value-goal)/goal)
		return closest
		
	def find_closest_l(self, goal):
		closest = self.binary_search_value(goal, self.ind)
		#closest.append(abs(closest.value-goal)/goal)
		return closest
		
	### multiple-component solvers
	def dual_additive_values(self, ntwrk, list):
		'''
		two components in additive form
		series for inductors and resistors
		parallel for capacitors
		
		finds best two values to meet the goal
		'''
		goal = ntwrk.goal
		max_val = goal*1.1 #set the max val a bit high in case the best match is slightly higher
		test_p1 = self.binary_search_value(max_val, list)
		p1_ind = list.index(test_p1)
		test_p2 = self.binary_search_value(goal - test_p1.value, list)
		
		ntwrk.impedance = self.add_components(test_p1, test_p2)
		ntwrk.error = abs(ntwrk.impedance.value-goal)/goal
		ntwrk.components = [test_p1, test_p2]
		
		# check the upper half of the values
		# checking the lower half would just transpose the components
		while test_p1.value > goal/2 and ntwrk.error != 0:
			imp = self.add_components(test_p1, test_p2)
			current_error = abs(imp.value-goal)/goal
			if current_error < ntwrk.error:
				ntwrk.impedance = imp
				ntwrk.error = current_error
				ntwrk.components = [test_p1, test_p2]
			
			p1_ind -= 1
			test_p1 = list[p1_ind]
			test_p2 = self.binary_search_value(goal - test_p1.value, list)
			
		return ntwrk		
		
	def dual_piggyback_values(self, ntwrk, list):
		'''
		two components in piggyback form
		parallel for inductors and resistors
		series for capacitors
		
		finds best two values to meet the goal
		'''
		goal = ntwrk.goal
		min_val = 2*goal*0.9 # make it a bit low in case the best match is a bit low
		test_p1 = self.binary_search_value(min_val, list)
		p1_ind = list.index(test_p1)
		test_p2 = self.binary_search_value(1/(1/goal - 1/test_p1.value), list)
		
		ntwrk.impedance = self.piggyback_components(test_p1, test_p2)
		ntwrk.error = abs(ntwrk.impedance.value-goal)/goal
		ntwrk.components = [test_p1, test_p2]
		
		# check the upper half of the values
		# checking the lower half would just transpose the components
		while p1_ind < len(list) and ntwrk.error != 0:
			imp = self.piggyback_components(test_p1, test_p2)
			current_error = abs(imp.value-goal)/goal
			if current_error < ntwrk.error:
				ntwrk.impedance = imp
				ntwrk.error = current_error
				ntwrk.components = [test_p1, test_p2]
			
			p1_ind += 1
			if (p1_ind < len(list)):
				test_p1 = list[p1_ind]
				test_p2 = self.binary_search_value(1/(1/goal - 1/test_p1.value), list)
			
		return ntwrk	
		
	### higher level tools
	def resistor_divider_calc(self, div_ratio, min_res, max_res):
		'''
		function to find resistance values that satisfy a resistive divider
		---/\/\/------/\/\/---
		    R1         R2
		resistance min_res < R1+R2 < max_res
		div_ratio = R2/(R1+R2)
		
		returns a PassiveNetwork object that specifies the resistances and ratio error
		'''
		if div_ratio == 0:
			return Passive()
		min_r2 = div_ratio * min_res
		if max_res == 0:
			max_res = self.res[-1].value
		max_r2 = div_ratio * max_res
		
		res_divider = PassiveNetwork('series', div_ratio)
		
		#start with the smallest it can be
		test_r2 = self.find_closest_r(min_r2)
		r2_ind = self.res.index(test_r2)
		test_r1 = self.find_closest_r(test_r2.value/div_ratio - test_r2.value)
		
		res_divider.impedance = self.add_components(test_r1, test_r2)
		res_divider.error = abs((test_r2.value/(test_r1.value+test_r2.value))-div_ratio)/div_ratio
		res_divider.components = [test_r1, test_r2]
		
		while test_r2.value < max_r2 and res_divider.error != 0:
			current_error = abs((test_r2.value/(test_r1.value+test_r2.value))-div_ratio)/div_ratio
			if current_error < res_divider.error:
				imp = self.add_components(test_r1, test_r2)
				res_divider.impedance = imp
				res_divider.error = current_error
				res_divider.components = [test_r1, test_r2]
			
			r2_ind += 1
			test_r2 = self.res[r2_ind]
			test_r1 = self.find_closest_r(test_r2.value/div_ratio - test_r2.value)
			
		return res_divider
#end class PassiveSolver

	
if __name__ == '__main__':
	# get the args
	import argparse

	parser = argparse.ArgumentParser(description='Find optimal network of passive components.')
	parser.add_argument('-r', nargs=1, type=float, dest='target_res',
						help='find closest discrete resistor to value (ohms)')
	parser.add_argument('-c', nargs=1, type=float, dest='target_cap',
						help='find closest discrete capacitor to value (picofarads)')
	parser.add_argument('-l', nargs=1, type=float, dest='target_ind',
						help='find closest discrete inductor to value (nanohenries)')
	parser.add_argument('-d', nargs=3, type=float, dest='res_divider_vals',
						help='find resistive divider: ratio min_res max_res')
	parser.add_argument('-r_file', nargs=1, dest='r_file',
						help='file of available resistor values')
	parser.add_argument('-c_file', nargs=1, dest='c_file',
						help='file of available capacitor values')
	parser.add_argument('-l_file', nargs=1, dest='l_file',
						help='file of available inductor values')

	args = parser.parse_args()
	
	# create a PassiveSolver
	ps = PassiveSolver()
	
	
	# execute the command
	# get the closest resistance if necessary
	if (args.target_res != None):
		if (args.r_file != None):
			ps.add_resistor_list(args.r_file)
		else:
			ps.add_resistor_list() #use default file
		print ps.find_closest_r(args.target_res[0])
		print ps.dual_additive_values(PassiveNetwork('series', args.target_res[0]), ps.res)
		print ps.dual_piggyback_values(PassiveNetwork('parallel', args.target_res[0]), ps.res)
	
	# get closest capacitance if necessary
	if (args.target_cap != None):
		if (args.c_file != None):
			ps.add_capacitor_list(args.c_file)
		else:
			ps.add_capacitor_list() #use default file
		print ps.find_closest_c(args.target_cap[0])
		print ps.dual_additive_values(PassiveNetwork('parallel', args.target_cap[0]), ps.cap)
		print ps.dual_piggyback_values(PassiveNetwork('series', args.target_cap[0]), ps.cap)
	
	# get closest inductance if necessary
	if (args.target_ind != None):
		if (args.l_file != None):
			ps.add_inductor_list(args.l_file)
		else:
			ps.add_inductor_list() #use default file
		print ps.find_closest_l(args.target_ind[0])
		print ps.dual_additive_values(PassiveNetwork('series', args.target_ind[0]), ps.ind)
		print ps.dual_piggyback_values(PassiveNetwork('parallel', args.target_ind[0]), ps.ind)
	
	# get resistor divider if necessary
	if (args.res_divider_vals != None):
		if (ps.res == []):
			if (args.r_file != None):
				ps.add_resistor_list(args.r_file)
			else:
				ps.add_resistor_list() #use default file
		print ps.resistor_divider_calc(args.res_divider_vals[0], args.res_divider_vals[1], args.res_divider_vals[2])