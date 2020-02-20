import csv
import re

minutesInDay = 60*24
day = {}

#Populate day variable with empty minutes
for i in range (0, minutesInDay+1):
	day[i] = 0


def getTimeInMinutes(time):
	split = re.split(':', time)

	hours = int(split[0])
	minutes = int(split[1])
	#seconds = int(split[2])

	minutes += 60*hours

	return minutes

	return 0


with open ('report.csv', 'r') as file:
	reader = csv.DictReader(file)
	for row in reader:
		startMinutes = getTimeInMinutes(row['Start time'])
		duration = getTimeInMinutes(row['Duration'])

		project = row['Project']


		#if not project in day.keys():
			#day[project] = {}

		#print(day)

		#if not project == 'Online Social':
		#	continue

		for i in range (startMinutes+1, startMinutes+duration+1):
			
			targetMinute = i

			if targetMinute >= 1440:
				targetMinute = abs(1440-i)

			day[targetMinute] += 1
	
del day[1440] # Remove this because otherwise we're considering midnight twice.

import matplotlib.pyplot as plt


plt.plot(list(day.keys()), list(day.values()), label="Total")


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


plt.show()