import time
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkcalendar import Calendar, DateEntry
from datetime import datetime, timedelta
import csv
import io
import re
import tempfile
import config
import math
from operator import itemgetter

class StartPage(tk.Frame):

	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent)
		self.controller = controller

		self.create_timeframe_controls()
		self.create_projects_frame()
		self.create_client_select()
		self.create_description_search()
		self.create_more_settings_button()
		self.create_highlight_current_time_button()
		self.create_create_graph_button()

	def create_timeframe_controls(self):
		timeframe_frame = Frame(self)
		timeframe_frame.grid(row=0, column=0, sticky='nw')

		timeframe_label = Label(timeframe_frame, text='Time Frame: ')
		timeframe_label.grid(row=0, column=0)

		self.timeframes = []

		current_timeframe_id = StringVar()
		current_timeframe_id.trace('w', self.change_timeframe)
		self.current_timeframe_id = current_timeframe_id

		self.timeframe_dropdown = OptionMenu(timeframe_frame, current_timeframe_id, value='test')
		self.timeframe_dropdown.grid(row=0, column=1)
		
		self.new_timeframe()
		self.update_timeframes_dropdown()

		current_timeframe_id.set(1)

		new_timeframe_button = ttk.Button(timeframe_frame, text="New Time Frame", command=self.new_timeframe)
		new_timeframe_button.grid(row=0, column=3)
		

	def update_timeframes_dropdown(self):
		menu = self.timeframe_dropdown['menu']

		menu.delete(0, 'end')

		i = 1

		for timeframe in self.timeframes:
			menu.add_command(label=i, command=lambda value=i: self.current_timeframe_id.set(value))
			i += 1

	def new_timeframe(self):
		frame = Frame(self)
		frame.grid(row=1, column=0, sticky='nw')
		bounds =self.controller.preset_date_bounds

		timeframe = {
			'frame': frame,
			'preset': self.create_timeframe_listbox(frame, bounds),
			'custom': self.create_custom_time_entry(frame),
			'name': self.create_timeframe_name_entry(frame)
		}

		self.timeframes.append(timeframe)

		self.update_timeframes_dropdown()

		highest_current_timeframe_id = len(self.timeframes)
		self.current_timeframe_id.set(highest_current_timeframe_id)

	def create_timeframe_name_entry(self, frame):
		label = ttk.Label(frame, text="Timeframe name: ")
		label.grid(row=0, column=0, sticky='e')

		default_name = str(len(self.timeframes) + 1)

		listbox = frame.winfo_children()[0]
		
		name = StringVar()
		name.trace('w', lambda name, index, mode: self.timeframe_updated(listbox))

		entry = Entry(frame, textvariable=name)
		entry.insert(0, 'Timeframe ' + default_name)
		entry.grid(row=0, column=1, sticky='w')

		return entry

	def create_timeframe_listbox(self, frame, bounds):

		listbox = Listbox(frame, selectmode=SINGLE, exportselection=False)
		listbox.grid(row=1, column=0, padx=10, pady=10, sticky='nw')

		for i in bounds:
			listbox.insert(END, i)

		listbox.bind('<<ListboxSelect>>', lambda event: self.timeframe_updated(listbox) )

		listbox.select_set(3)

		return listbox


	def create_custom_time_entry(self, container_frame):
		listbox = container_frame.winfo_children()[0] # TODO: Find a better way to access this listbox than simply quoting the ID.
		
		frame = LabelFrame(container_frame, text="Custom Time Frame", padx=10, pady=10)

		start_label = ttk.Label(frame, text="Start Date:")
		start_label.grid(row=0, column=0, padx=10, pady=10)

		start_select = DateEntry(frame)
		start_select.grid(row=0, column=1, padx=10, pady=10)
		start_select.bind('<<DateEntrySelected>>', lambda event: self.timeframe_updated(listbox))

		end_label = ttk.Label(frame, text="End Date:")
		end_label.grid(row=1, column=0, padx=10, pady=10)

		end_select = DateEntry(frame)
		end_select.grid(row=1, column=1, padx=10, pady=10)
		end_select.bind('<<DateEntrySelected>>', lambda event: self.timeframe_updated(listbox))

		return frame

	def change_timeframe(self, *virtual_event):
		current_timeframe_id = self.current_timeframe_id.get()
		all_timeframes = self.timeframes
		current_timeframe = all_timeframes[int(current_timeframe_id)-1]

		for timeframe in all_timeframes:
			timeframe['frame'].grid_forget()

		current_timeframe['frame'].grid(row=1, column=0)

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

	def timeframe_updated(self, listbox):
		selected_timeframe_name = self.get_listbox_value(listbox)[0]

		using_custom_timeframe = True if selected_timeframe_name == 'Custom' else False
		self.toggle_custom_date_input(using_custom_timeframe)

		date_bounds = self.get_date_bounds_from_timeframe(selected_timeframe_name)

		current_timeframe_id = int(self.current_timeframe_id.get())

		self.controller.date_bounds[current_timeframe_id] = date_bounds

	def get_date_bounds_from_timeframe(self, timeframe_name):
		current_timeframe_id = int(self.current_timeframe_id.get())
		timeframe = self.timeframes[current_timeframe_id-1]
		name = timeframe['name'].get()

		if timeframe_name == 'Custom':
			children = timeframe['custom'].winfo_children()

			start = children[1].get_date()
			end = children[3].get_date() #TODO - Find a better way to access the date entry elements, instead of quoting their IDs.

			date_bounds = {
				'start': datetime.combine(start, datetime.min.time()), # We change these to datetimes since we need to compare with Toggl's time
				'end': datetime.combine(end, datetime.min.time()),
				'name': name
			}
		else:
			number_of_days = self.controller.preset_date_bounds[timeframe_name]

			date_bounds = {
				'start': datetime.now() - timedelta(days=number_of_days),
				'end': datetime.now(),
				'name': name
			}

		return date_bounds


	# Hide/show the custom date input box	
	def toggle_custom_date_input(self, value):
		if not self.timeframes:
			return False

		current_timeframe_id = int(self.current_timeframe_id.get())

		if value == True:
			self.timeframes[current_timeframe_id-1]['custom'].grid(row=1, column=1, padx=10, pady=10, sticky='nw')
		else:
			self.timeframes[current_timeframe_id-1]['custom'].grid_forget()
	
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

		client_projects = self.get_client_projects()
		self.populate_project_listbox(project_list = client_projects)
		self.project_listbox_updated()

		#TODO - Fix toggle buttons. Maybe write new function: change_toggle_behavior, which takes a button and all/none as argument.

		number_of_client_projects = len(client_projects)
		number_of_selected_projects = len(self.controller.project_list)
		button = self.projects_select_all_button
		
		if number_of_selected_projects == number_of_client_projects:
			button.config(text = 'Select None')
		else:
			button.config(text = 'Select All')
		

	def get_client_projects(self):
		all_projects = self.controller.master_project_list
		selected_clients = self.controller.client_list

		client_projects = []

		for project_data in all_projects.values():
			if project_data['client'] in selected_clients:
				client_projects.append(project_data['name'])

		return client_projects

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

	def create_highlight_current_time_button(self):
		enable_highlight = IntVar()
		enable_highlight.set(1)

		box = Checkbutton(self, text="Highlight current time", variable=enable_highlight)
		box.grid(row=2, column=1, padx=10, pady=10, sticky='w')

		self.controller.highlight_current_time = enable_highlight

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

		group_by_options = ['Project', 'Client', 'Tag', 'Description', 'Timeframe', 'None']

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