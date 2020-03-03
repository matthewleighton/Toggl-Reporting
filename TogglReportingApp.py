"""
#To Do List:
- !!! Refactor code to join together project and client functions. Much of this is the same, and can be combined !!!
- Add "No Client" client, to include projects with no client. Currently they're being excluded.
- Make it more efficient by only grabbing all the data once upon login. We don't need to be making new requests for every graph.
- Ability to show multiple graphs at once
- Rename "More Settings" button to "Grouping Settings"
- Add title to graph, showing timespan.
- Search by client
- Some kind of search via tags
- Ability to save/load different configurations of settings
- Ability to manually enter Toggl info to login, and switch between accounts.
- Some kind of "search" function for descriptions. Able to search for description of particular project
- Add "Ignore" tickbox next to each description. To temporarily disable it.
- Option to add 'Now' line onto graph
- Multiple time frames, and group by time frame. So we can see how tracking changes in span 1 vs span 2.
- If a line is at zero across the whole graph, remove it. (?)
"""

import time
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkcalendar import Calendar, DateEntry
from toggl.TogglPy import Toggl

from datetime import datetime, timedelta

import csv
import io
import re

import tempfile

import matplotlib.pyplot as plt

import config

import math
from operator import itemgetter
import pprint

LARGE_FONT = ("Verdana", 12)

# TogglReportingApp Class -------------------------------------------------------------------------------------------
class TogglReportingApp(tk.Tk):

	def __init__(self, *args, **kwargs):
		self.connect_to_toggl()
		self.get_toggl_project_data()
		self.define_preset_date_bounds()
		
		self.group_by = 'Project'
		self.description_groupings = []


		tk.Tk.__init__(self, *args, **kwargs)

		tk.Tk.wm_title(self, "Toggl Reporting")

		container = ttk.Frame(self)
		container.pack(side="top", fill="both", expand=True)
		container.grid_rowconfigure(0, weight=1)
		container.grid_columnconfigure(0, weight=1)

		self.frames = {}

		frame = StartPage(container, self)
		self.frames[StartPage] = frame
		frame.grid(row=0, column=0, sticky='nsew')

		"""
		for F in (StartPage):
			frame = F(container, self)

			self.frames[F] = frame

			frame.grid(row=0, column=0, sticky="nsew")
		"""

		self.show_frame(StartPage)

	def show_frame(self, cont):
		frame=self.frames[cont]
		frame.tkraise()

	# Establish the connection to the TogglAPI, and collect the project data.
	def connect_to_toggl(self):
		self.toggl = Toggl()
		self.toggl.setAPIKey(config.API_KEY)
	
	# Get information about the user's projects from Toggl	
	def get_toggl_project_data(self):
		self.user_data = self.toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")

		project_data 	  = self.remove_empty_projects(self.user_data['data']['projects'])
		project_data_dict = {project_data[i]['name']: project_data[i] for i in range(0, len(project_data))}

		self.master_project_list = project_data_dict # Unchanging "master" list
		self.project_list 		 = project_data_dict.copy().keys() # List of active projects to be displayed in the graph

		client_data 	 = self.user_data['data']['clients']
		client_data_dict = {client_data[i]['name']: client_data[i] for i in range(0, len(client_data))}

		self.master_client_list  = client_data_dict # Unchanging "master" list
		self.client_list 		 = client_data_dict # List of active projects to be displayed in the graph

		# Assigning clients to projects.
		for client in client_data:
			client_id = client['id']
			client_name = client['name']

			for project_name in self.master_project_list:				
				if not 'cid' in self.master_project_list[project_name]:
					self.master_project_list[project_name]['client'] = False
				elif self.master_project_list[project_name]['cid'] == client_id:
					self.master_project_list[project_name]['client'] = client_name

		self.project_list = self.master_project_list

	# Return a version of the project list, where all projects without any tracked hours are removed.
	# (This also removes projects which have been deleted via Toggl, but are still retrieved via the API)
	def remove_empty_projects(self, project_list):
		to_delete = []
		for i in range(0, len(project_list)):
			if not 'actual_hours' in project_list[i]:
				to_delete.append(i)

		for i in sorted(to_delete, reverse=True):
			del project_list[i]

		return project_list

	def define_preset_date_bounds(self):
		year = 365
		month = 30

		self.preset_date_bounds = {
			'Past Week': 	 7,
			'Past Month': 	 month,
			'Past 6 Months': month*6,
			'Past Year': 	 year,
			'Past 2 Years':  year*2,
			'Past 5 Years':  year*5,
			'Custom':0
		}

	def set_group_by(self, group_by):
		self.group_by = group_by

	# Make a request to Toggl to get a report of all data from a given time frame.
	def get_report(self, params):
		data = {
		    'workspace_id': config.WORKSPACE_ID,
		    'since': params['start'],
		    'until': params['end'],
		}

		return self.toggl.getDetailedReportCSV(data)

	def is_included_project(self, project):
		if project in self.project_list:
			return True
		else:
			return False

	def is_included_client(self, client):
		if client in self.client_list:
			return True
		else:
			return False

	def main_sequence(self):
		self.update_project_data()
		self.update_client_data()
		self.update_description_restrictions()

		report = self.get_report_from_toggl()

		day = self.get_day()
		day = self.populate_day(day, report)

		self.create_graph(day)

	def update_project_data(self):
		user_selection = self.project_list
		self.project_list = {}

		for project_name in user_selection:
			self.project_list[project_name] = self.master_project_list[project_name]

	def update_client_data(self):
		user_selection = self.client_list
		self.client_list = {}

		for client_name in user_selection:
			self.client_list[client_name] = self.master_client_list[client_name]


	def get_report_from_toggl(self):
		# Split the request into several with a max length of one year. (Toggl API only allows reports of max 1 year length)
		split_bounds = self.split_date_bounds(self.date_bounds)

		# A list of all the reports we gather from Toggl. (Max 1 year each)
		reports = []

		for bounds in split_bounds:
			params = {
				'start': bounds['start'],
				'end': bounds['end']
			}

			reports.append(app.get_report(params))

		return self.join_reports(reports)

	# Return a list containing a series of bounds, each of at most 1 year long.
	def split_date_bounds(self, bounds):
		span = self.get_report_span(bounds['start'], bounds['end'])

		number_of_years = math.ceil(span/365)

		bounds = []

		for year in range(number_of_years):
			remaining_days_after_subtraction = span - 365
			
			start = datetime.now() - timedelta(days = span)

			if (remaining_days_after_subtraction > 0):
				span = remaining_days_after_subtraction	
				end = datetime.now() - timedelta(days = span + 1) #(Plus 1 so we don't get an overlap at the edge of the bounds)
			else:
				end = datetime.now()

			bounds.append(
				{
					'start': start,
					'end': end
				}
			)

		return bounds

	# Return the length of time that a report covers. (In days)
	def get_report_span(self, start, end):
		span = end - start
		return span.days

	# Join the given reports together, saving them as a temporary csv file.
	def join_reports(self, reports_list):
		filename = 'test.csv'

		test = ''

		temporary_csv_file = tempfile.NamedTemporaryFile()

		for report in reports_list:

			with open(temporary_csv_file.name, 'ab') as csv:
				csv.write(report)

		return temporary_csv_file

	def update_description_restrictions(self):
		self.allowed_descriptions = []
		self.excluded_descriptions = []

		for i in self.description_search_list:
			description_row = self.description_search_list[i]
			value 			= description_row['entry'].get().lower()
			excluded 		= bool(description_row['exclude_checkbox_value'].get())

			if excluded:
				self.excluded_descriptions.append(value)
			else:
				self.allowed_descriptions.append(value)

		# If there are no specifically allowed descriptions, say that an empty string is allowed. (Otherwise we'll return nothing).
		if not self.allowed_descriptions:
			self.allowed_descriptions = ['']

	# Return an dictionary containing projects with minutes set to zero.
	def get_day(self):
		minutesInDay = 60*24
		day = {}
		emptyDay = {}

		for i in range (0, minutesInDay+1):
			emptyDay[i] = 0

		if self.group_by == 'Project':
			for project in self.project_list:
				day[project] = emptyDay.copy()

		if self.group_by == 'Description':
			for grouping in self.description_groupings:
				day[grouping['title']] = emptyDay.copy()
		if self.group_by == 'None':
			day = emptyDay

		return day

	# Populate the day dictionary with data from the report.
	def populate_day(self, day, report):
		with open (report.name, 'r') as file:
			reader = csv.DictReader(file)
			for row in reader:

				project 	= row['Project']
				description = row['Description']
				client 		= row['Client']
				
				# Skipping header rows from merged csv.
				if row['Email'] == 'Email':
					continue

				if not self.is_included_project(project):
					continue

				if not self.is_included_client(client):
					continue

				description_match = False

				if self.group_by == 'Description':
					matched_description_groups = []

					for description_grouping in self.description_groupings:
						for user_description in description_grouping['descriptions']:
							if user_description in description.lower():
								description_match = True
								grouping_title = description_grouping['title']
								if not grouping_title in matched_description_groups:
									matched_description_groups.append(grouping_title)
				else:
					for allowed_description in self.allowed_descriptions:
						if allowed_description in description.lower():
							description_match = True
							break

					for excluded_description in self.excluded_descriptions:
						if excluded_description in description.lower():
							description_match = False

					if not description_match:
						continue

				startMinutes = self.getTimeInMinutes(row['Start time'])
				duration = self.getTimeInMinutes(row['Duration'])

				for i in range (startMinutes+1, startMinutes+duration+1):
					
					targetMinute = i

					if targetMinute >= 1440:
						targetMinute = abs(1440-i)

					if self.group_by == 'Project':
						day[project][targetMinute] += 1
					elif self.group_by == 'Description':
						for description_group in matched_description_groups:
							day[description_group][targetMinute] += 1
					elif self.group_by == 'None':
						day[targetMinute] += 1

		return day

	def getTimeInMinutes(self, time):
		split = re.split(':', time)

		hours = int(split[0])
		minutes = int(split[1])

		minutes += 60*hours

		return minutes

	def create_graph(self, day):
		if self.group_by == 'Project':
			for project_name in self.project_list:

				hex_color = self.project_list[project_name]['hex_color']

				plt.plot(list(day[project_name].keys()), list(day[project_name].values()), label=project_name, color=hex_color)
		elif self.group_by == 'Description':
			for grouping in self.description_groupings:
				title = grouping['title']
				plt.plot(list(day[title].keys()), list(day[title].values()), label=title)
		elif self.group_by == 'None':
			plt.plot(list(day.keys()), list(day.values()))


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

# -----------------------------------------------------------------------------------------------------------
# StartPage Class -------------------------------------------------------------------------------------------
class StartPage(tk.Frame):

	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent)
		self.controller = controller

		self.create_custom_time_input()
		self.create_time_frame_listbox()
		self.create_projects_frame()
		self.create_client_select()
		self.create_description_search()
		self.create_more_settings_button()
		self.create_create_graph_button()

	# Create the input selector for the time frame.
	def create_time_frame_listbox(self):
		self.time_frame_frame = LabelFrame(self, text="Time Frame")
		self.time_frame_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nw')

		self.time_frame_listbox = Listbox(self.time_frame_frame, selectmode=SINGLE, exportselection=False)
		self.time_frame_listbox.grid(row=1, column=0, padx=10, pady=10)

		for i in self.controller.preset_date_bounds:
			self.time_frame_listbox.insert(END, i)

		self.time_frame_listbox.bind('<<ListboxSelect>>', self.time_frame_updated)

		self.time_frame_listbox.select_set(3) # Default to past year. TODO: Shouldn't depend on specific ID.

		self.time_frame_updated()

	def get_listbox_value(self, listbox):
		selected_ids = listbox.curselection()

		selected_names = []

		for id in selected_ids:
			selected_names.append(listbox.get(id))

		return selected_names

		if len(selected_names) == 1:
			return selected_names[0]
		else:
			return selected_names

	def time_frame_updated(self, *args):
		listbox = self.time_frame_listbox

		selected_time_frame = self.get_listbox_value(listbox)[0]
		using_custom_time_frame = True if selected_time_frame == 'Custom' else False
		self.toggle_custom_date_input(using_custom_time_frame)

		date_bounds = self.get_date_bounds_from_time_frame(selected_time_frame)

		self.selected_time_frame = selected_time_frame

	def get_date_bounds_from_time_frame(self, date_bounds):
		number_of_days = self.controller.preset_date_bounds[date_bounds]

		self.controller.date_bounds = {
			'start': datetime.now() - timedelta(days=number_of_days),
			'end': datetime.now()
		}

	# Hide/show the custom date input box	
	def toggle_custom_date_input(self, value):
		if value == True:
			self.custom_time_input_frame.grid(row=1, column=0, padx=10, pady=10, sticky='ne')
		else:
			self.custom_time_input_frame.grid_forget()

	# Create the frame for the input of custom time bounds.
	def create_custom_time_input(self):
		self.custom_time_input_frame = LabelFrame(self, text="Custom Time Frame", padx=10, pady=10)

		self.start_label = ttk.Label(self.custom_time_input_frame, text="Start Date:")
		self.start_label.grid(row=0, column=0, padx=10, pady=10)

		self.start_select = DateEntry(self.custom_time_input_frame)
		self.start_select.grid(row=0, column=1, padx=10, pady=10)
		self.start_select.bind('<<DateEntrySelected>>', self.update_custom_time_frame_values)

		self.end_label = ttk.Label(self.custom_time_input_frame, text="End Date:")
		self.end_label.grid(row=1, column=0, padx=10, pady=10)

		self.end_select = DateEntry(self.custom_time_input_frame)
		self.end_select.grid(row=1, column=1, padx=10, pady=10)
		self.end_select.bind('<<DateEntrySelected>>', self.update_custom_time_frame_values)

	def update_custom_time_frame_values(self, virtual_event):
		self.date_bounds = {
			'start': self.start_select.get_date(),
			'end': self.end_select.get_date()
		}

	def create_projects_frame(self):
		self.project_selector_frame = LabelFrame(self, text="Projects", padx=10, pady=10)

		sort_orders = ['Time Tracked', 'Alphabetical']
		self.project_sort_order = StringVar()
		self.project_sort_order.set(sort_orders[0])
		self.project_sort_order.trace('w', self.populate_project_listbox)

		self.project_sort_order_dropdown = OptionMenu(self.project_selector_frame, self.project_sort_order, *sort_orders)
		self.project_sort_order_dropdown.grid(row=0, column=0, pady=5)

		self.project_listbox = Listbox(self.project_selector_frame, selectmode=MULTIPLE, exportselection=False)
		self.project_listbox.grid(row=1, column=0)
		self.project_listbox.bind('<<ListboxSelect>>', self.project_listbox_updated)
		self.populate_project_listbox()
		

		#command=lambda: self.delete_description_search(description_id, entry)

		self.projects_select_all_button = ttk.Button(self.project_selector_frame, text="Select All", command=lambda: self.toggle_all('project'))
		self.projects_select_all_button.grid(row=2, column=0, padx=10, pady=10)

		self.project_selector_frame.grid(row=1, column=3, padx=10, pady=10)

	def project_listbox_updated(self, virtual_event=False):
		self.controller.project_list = self.get_listbox_value(self.project_listbox)

	def create_client_select(self):
		self.client_listbox_frame = LabelFrame(self, text='Clients', padx=10, pady=10)
		self.client_listbox_frame.grid(row=1, column=4, padx=10, pady=10)

		self.client_listbox = Listbox(self.client_listbox_frame, selectmode=MULTIPLE, exportselection=False)
		self.populate_client_listbox()
		self.client_listbox.grid(row=1, column=0)
		self.client_listbox.bind('<<ListboxSelect>>', self.client_listbox_updated)

		self.clients_select_all_button = ttk.Button(self.client_listbox_frame, text="Select None", command=lambda: self.toggle_all('client'))
		self.clients_select_all_button.grid(row=2, column=0, padx=10, pady=10)

	def populate_client_listbox(self):
		self.client_listbox.delete(0, END)

		client_list = self.controller.master_client_list

		client_list = sorted(client_list.values(), key=itemgetter('name'))

		for client in client_list:
			self.client_listbox.insert(END, client['name'])

		self.client_listbox.select_set(0, END) # Select all clients by default.

	def client_listbox_updated(self, virtual_event=False):
		self.controller.client_list = self.get_listbox_value(self.client_listbox)

		number_of_total_clients = len(self.controller.master_client_list)
		number_of_selected_clients = len(self.controller.client_list)
		button = self.clients_select_all_button

		if number_of_selected_clients == number_of_total_clients:
			button.config(text = 'Select None')
		else:
			button.config(text = 'Select All')

		self.hide_nonclient_projects()

	def hide_nonclient_projects(self):
		all_projects = self.controller.master_project_list
		selected_clients = self.controller.client_list

		client_projects = []

		for project_data in all_projects.values():
			if project_data['client'] in selected_clients:
				client_projects.append(project_data['name'])

		self.populate_project_listbox(project_list = client_projects)


	def get_project_client(self, project_name):
		project_data = self.controller.master_project_list[project_name]
		return project_data['client']

	# Populate the projects selector list, according to the chosen sort order.
	def populate_project_listbox(self, *virtual_event, project_list = False):
		listbox = self.project_listbox
		original_project_selection = self.get_listbox_value(listbox)

		self.project_listbox.delete(0, END) # Remove old contents of list.

		sort_order = self.project_sort_order.get()

		if project_list == False:
			project_list = self.controller.master_project_list
		else:
			project_list_dict = {}

			master_project_list = self.controller.master_project_list
			for project_name in master_project_list:
				if project_name in project_list:
					project_list_dict[project_name] = master_project_list[project_name]	
				
			project_list = project_list_dict


		if sort_order == 'Alphabetical':
			project_list = sorted(project_list.values(), key=itemgetter('name'))
		else:
			project_list = sorted(project_list.values(), key=itemgetter('actual_hours'))
			project_list.reverse()

		for project in project_list:
			self.project_listbox.insert(END, project['name'])

		visible_projects = listbox.get(0, END)
		
		i = 0
		for project in visible_projects:
			if project in original_project_selection:
				listbox.select_set(i)
			i += 1

	# Toggle the selection of projects or clients, depending on value of category_type.
	def toggle_all(self, category_type):
		listbox = getattr(self, category_type + '_listbox')
		button = getattr(self, category_type + 's_select_all_button')

		number_in_category = listbox.size()
		number_selected = len(listbox.curselection())

		if number_selected == number_in_category: # Unselect all projects
			listbox.selection_clear(0, END)
			button.config(text = 'Select All')
		else: # Select all projects
			listbox.select_set(0, END)
			button.config(text = 'Select None')

		update_function = getattr(self, category_type + '_listbox_updated')
		update_function()

	def create_description_search(self):
		self.description_search_frame = LabelFrame(self, text='Description', padx=10, pady=10)

		self.description_id = 1


		self.controller.description_search_list = {}

		self.add_new_description_search()

		self.description_search_frame.grid(row=1, column=0, padx=10, pady=10, sticky='sw')

	def add_new_description_search(self):
		frame = Frame(self.description_search_frame)

		# ID of the user's description. We use this to keep track of them when the user deletes descriptions.
		description_id = self.description_id
		row = len(self.controller.description_search_list)

		entry = Entry(frame, textvariable='')
		entry.grid(row=row, column=0)

		new_description_button = ttk.Button(frame, text="+", command=self.add_new_description_search)
		new_description_button.grid(row=row, column=1)

		delete_description_button = ttk.Button(frame, text="-", command=lambda: self.delete_description_search(description_id, entry))
		delete_description_button.grid(row=row, column=2)

		exclude_checkbox_value = IntVar()
		exclude_checkbox = Checkbutton(frame, text='Exclude', variable=exclude_checkbox_value)
		exclude_checkbox.grid(row=row, column=5)

		self.controller.description_search_list[self.description_id] = {
			'frame': frame,
			'entry': entry,
			'exclude_checkbox': exclude_checkbox,
			'exclude_checkbox_value': exclude_checkbox_value
		}

		frame.pack()

		self.description_id += 1

	def delete_description_search(self, description_id, entry):
		if len(self.controller.description_search_list) < 2:
			entry.delete(0, 'end')
		else:
			description = self.controller.description_search_list[description_id]
			description['frame'].destroy()
			del self.controller.description_search_list[description_id]

	def create_more_settings_button(self):
		button = ttk.Button(self, text='More Settings', command=self.display_more_settings)
		button.grid(row=2, column=0, padx=10, pady=10, sticky='w')

	def display_more_settings(self):
		self.settings_window = Toplevel(self)
		self.create_description_grouping_frame()
		self.create_group_by_frame()

		self.settings_window.protocol('WM_DELETE_WINDOW', self.close_more_settings_window)
		
		self.settings_window.grab_set()

	def close_more_settings_window(self):
		group_by = self.group_by_listbox.get(self.group_by_listbox.curselection())
		self.controller.group_by = group_by
		self.controller.description_groupings = []

		if group_by == 'Description':
			for description_group in self.description_grouping_listboxes:
				title = description_group['entry'].get()
				descriptions = description_group['listbox'].get(0, END)

				if len(descriptions) == 0:
					continue
				
				self.controller.description_groupings.append({
					'title': title,
					'descriptions': descriptions
					})

		self.settings_window.destroy()

	def create_group_by_frame(self):
		self.group_by_frame = LabelFrame(self.settings_window, text="Group by", padx=10, pady=10)

		self.group_by_listbox = Listbox(self.group_by_frame, selectmode=SINGLE, exportselection=False)

		group_by_options = ['Project', 'Client', 'Tag', 'Description', 'None']

		for i in group_by_options:
			self.group_by_listbox.insert(END, i)

		current_group_by = self.controller.group_by
		current_group_by_id = self.group_by_listbox.get(0, END).index(current_group_by)

		self.group_by_listbox.bind('<<ListboxSelect>>', self.check_group_by_selection)
		self.group_by_listbox.select_set(current_group_by_id)
		self.check_group_by_selection()
		self.group_by_listbox.pack()
		self.group_by_frame.grid(row=0, column=0, sticky='w')
		
	def check_group_by_selection(self, *args):
		group_by = self.group_by_listbox.get(self.group_by_listbox.curselection())
		self.controller.set_group_by(group_by)

		if group_by == 'Description':
			description_groupings = True
		else:
			description_groupings = False

		self.toggle_description_grouping(description_groupings)

	# Toggle whether the descriptions grouping frame is displayed or not.
	def toggle_description_grouping(self, value):
		if value == True:
			self.description_grouping_frame.grid(row=5, column=0)
		else:
			self.description_grouping_frame.grid_forget()

	def create_description_grouping_frame(self):
		controller = self.controller

		self.description_grouping_frame = LabelFrame(self.settings_window, text='Grouping by Descriptions', padx=10, pady=10)

		controller.update_description_restrictions()
		description_list = controller.allowed_descriptions

		self.description_grouping_listboxes = []

		existing_description_groupings = controller.description_groupings

		column = 0
		if len(existing_description_groupings) == 0:
			for description in description_list:
				self.create_description_grouping_listbox(description, column)
				column += 1	
		else:
			old_descriptions = []
			for grouping in existing_description_groupings:
				descriptions = list(grouping['descriptions'])

				# Ignore descriptions which have been removed from the description list by the user.
				for description in descriptions:
					if not description in description_list:
						descriptions.remove(description)

				title = grouping['title']
				self.create_description_grouping_listbox(descriptions, column, title)
				
				old_descriptions.extend(descriptions)
				column += 1

			new_descriptions = list(set(description_list)-(set(old_descriptions)))

			for description in new_descriptions:
				self.create_description_grouping_listbox(description, column)
				column += 1

			while column < len(description_list):
				self.create_description_grouping_listbox([], column)
				column += 1
				
		move_description_buttons = Frame(self.description_grouping_frame)

		left_button = ttk.Button(move_description_buttons, text="<<", command=lambda: self.move_description('left'))
		left_button.grid(row=0, column=0)

		right_button = ttk.Button(move_description_buttons, text=">>", command=lambda: self.move_description('right'))
		right_button.grid(row=0, column=1)

		move_description_buttons.grid(row=10, column=0, sticky='w')

		self.description_grouping_frame.grid(row=5, column=0, sticky='w')

	def create_description_grouping_listbox(self, descriptions, column, title=False):
		frame = Frame(self.description_grouping_frame)

		if not title:
			title = descriptions

		entry = Entry(frame)
		entry.insert(0, title)
		entry.config(state='disabled')
		entry.pack()

		if isinstance(descriptions, str):
			description = descriptions
			descriptions = [description]

		listbox = Listbox(frame, selectmode=SINGLE, exportselection=True)
		
		for description in descriptions:
			listbox.insert(END, description)	

		listbox.pack()

		frame.grid(row=0, column=column)

		self.description_grouping_listboxes.append({
				'grouping_id': column,
				'frame': frame,
				'entry': entry,
				'listbox': listbox
			})

	def move_description(self, direction):
		for description_group in self.description_grouping_listboxes:
			grouping_id = description_group['grouping_id']
			listbox = description_group['listbox']
			selected_value_id = listbox.curselection()
			if selected_value_id:
				break

		max_grouping_id = len(self.description_grouping_listboxes)-1
		id_adjustment   = 1 if direction == 'right' else -1
		new_grouping_id = grouping_id + id_adjustment

		# Check if we're trying to move left/right from edge of table.
		if new_grouping_id < 0 or new_grouping_id > max_grouping_id:
			return

		old_grouping_id = grouping_id

		selected_description = listbox.get(listbox.curselection())
		listbox.delete(selected_value_id)

		new_listbox = self.description_grouping_listboxes[new_grouping_id]['listbox']
		new_listbox.insert(END, selected_description)
		new_listbox.select_set(END)

		new_listbox_values = new_listbox.get(0, END)
		old_listbox_values = listbox.get(0, END)

		self.toggle_active_description_group_title(old_grouping_id)
		self.toggle_active_description_group_title(new_grouping_id)
			
	# Display the correct title, and active/disabled state of a description listbox.
	def toggle_active_description_group_title(self, grouping_id):
		grouping 			   = self.description_grouping_listboxes[grouping_id]
		entry 				   = grouping['entry']
		listbox_values 		   = grouping['listbox'].get(0, END)
		number_of_descriptions = len(listbox_values)

		entry.config(state='normal')

		if number_of_descriptions < 2:
			entry.config(state='normal')
			entry.delete(0, 'end')

			if number_of_descriptions == 1:
				entry_value = listbox_values[0]
				entry.insert(0, entry_value)

			entry.config(state='disabled')

	def create_create_graph_button(self):
		create_graph_button = ttk.Button(self, text="Create Graph", command=self.confirm_user_selection)
		create_graph_button.grid(row=2, column=3, padx=10, pady=10, sticky='se')

	# The user has finished inputting values. Now begin the work of generating the graph.
	def confirm_user_selection(self):
		self.controller.main_sequence()

	def assign_chosen_clients(self):
		chosen_clients = [self.client_listbox.get(idx) for idx in self.client_listbox.curselection()]
		self.controller.client_list = {}

		for client_name in chosen_clients:
			self.controller.client_list[client_name] = self.controller.master_client_list[client_name]

		self.controller.show_frame(StartPage)

app = TogglReportingApp()

app.mainloop()