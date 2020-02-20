import csv
import re

minutesInDay = 60*24
day = {}

emptyDay = {}
#Populate day variable with empty minutes
for i in range (0, minutesInDay+1):
	emptyDay[i] = 0

projectList = [
	'Physics',
	'Maths',
	'Reading',
	'Film/TV',
	'Coding',
	'Real Life Social',
	'Online Social',
	'Video Games',
	#'Total'
]

for project in projectList:
	day[project] = emptyDay.copy()


def getTimeInMinutes(time):
	split = re.split(':', time)

	hours = int(split[0])
	minutes = int(split[1])
	#seconds = int(split[2])

	minutes += 60*hours

	return minutes

	return 0

def isValidProject(project):
	if project in projectList:
		return True
	
	return False


with open ('report.csv', 'r') as file:
	reader = csv.DictReader(file)
	for row in reader:
		startMinutes = getTimeInMinutes(row['Start time'])
		duration = getTimeInMinutes(row['Duration'])

		project = row['Project']

		if not isValidProject(project):
			continue
	



		#if not project in day.keys():
			#day[project] = {}

		#print(day)

		#if not project == 'Online Social':
		#	continue

		for i in range (startMinutes+1, startMinutes+duration+1):
			
			targetMinute = i

			if targetMinute >= 1440:
				targetMinute = abs(1440-i)

			day[project][targetMinute] += 1
			#day['Total'][targetMinute] += 1
	
#for prject in day:
	#del day[project][1440]# Remove this because otherwise we're considering midnight twice.




import matplotlib.pyplot as plt


for project in projectList:
	plt.plot(list(day[project].keys()), list(day[project].values()), label=project)


plt.ylabel('Frequency')

positions = []
labels = []

for i in range(0, 24):
	positions.append(i*60)

	time = str(i) + ':00'

	if len(time) < 5:
		time = '0' + time

	labels.append(time)

plt.xticks(positions, labels)

plt.grid()

plt.legend()

plt.show()