import sys
import os
wd = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(wd, '../..'))
import json

import numpy as np
from bay.access_bay import AccessBay
from examples_gen.rand_lane_gen import RandLaneGen

class InstanceLoader(): 
    def __init__(self, instance_file): 
        instance_file = self._preprocessing_instance_file(instance_file)
        self.layout_file_name = instance_file["layout_file"].split("/")[-1].split(".")[0]
        self.fill_level = instance_file["fill_level"]
        self.max_priority = instance_file["max_priority"]
        self.height = instance_file["height"]
        self.seed = instance_file["seed"]
        example_bay = list(instance_file["bay_info"].keys())[0]
        self.access_directions = self._create_access_directions_dict(instance_file["bay_info"][example_bay]["access_directions"])
        self.inital_state = instance_file["initial_state"]
        self.bay_info = instance_file["bay_info"]
        # Try except here to catch old instance files where the sink was not implemented yet
        try:    
            self.sink = instance_file["sink"]
        except: 
            self.sink = False
        try:
            self.source = instance_file["source"]
        except: 
            self.source = False

        # Time window related variables
        if self.max_priority == 0: 
            self.unit_loads = instance_file["unit_loads"]
            
    def __str__(self): 
        return str({
            "layout_file_name": self.layout_file_name,
            "fill_level": self.fill_level,
            "max_p": self.max_priority,
            "height": self.height,
            "seed": self.seed,
            "access_directions": self.access_directions,
            "initial_state": self.inital_state,
        })

    def _preprocessing_instance_file(self, instance_file): 
        """
        This function allows to either pass a path to the instance file or directly a instance json
        """
        try: 
            if isinstance(instance_file, str): 
                with open(instance_file, "r") as f: 
                    instance_file = json.load(f)
            _ = instance_file["layout_file"].split("/") # Test for TypeError
            return instance_file
        except TypeError: 
            print(f"Error: Make sure that you pass a path to an instance file or a dictionary to the InstanceLoader.\n You passed {instance_file}")
            sys.exit(1)

    def _create_access_directions_dict(self, access_directions): 
        north, east, south, west = False, False, False, False
        if "north" in access_directions: 
            north = True
        if "east" in access_directions: 
            east = True
        if "south" in access_directions: 
            south = True
        if "west" in access_directions: 
            west = True
        return {
            "north": north, 
            "east" : east,
            "south": south,
            "west" : west
        }

    def generate_bays_priorities(self, bays, height: int=0):
        """Generates random lanes and populates them with stacks 
        TODO: implement for unit loads
        """
        for bay in bays: 
            bay.height = height
            bay.state = np.zeros((bay.length, bay.width, bay.height), dtype=int)
            self._fill_bay(bay)

    def _fill_bay(self, bay: AccessBay): 
        bay_key = self._bay_finder(bay.x, bay.y)
        state = self.inital_state[bay_key]
        bay.state = np.asarray(state)

    def _bay_finder(self, x, y): 
        for bay_key in self.bay_info: 
            bay_info_value = self.bay_info[bay_key]
            if bay_info_value["x"] == x and bay_info_value["y"] == y:
                return bay_key
        print("Bay could not be found in the given JSON with the x and y coordinates. This Instance file seems to be manipulated.")
        sys.exit(1)

    def get_initial_state(self): 
        return self.inital_state

    def get_layout_filename(self): 
        return f"examples/{self.layout_file_name}.csv"
    
    def get_access_directions(self): 
        return self.access_directions

    def get_max_p(self):
        return self.max_priority
    
    def get_fill_level(self):
        return self.fill_level

    def get_height(self):
        return self.height
    
    def get_seed(self):
        return self.seed
    
    def get_access_directions(self):
        return self.access_directions

    def get_sink(self): 
        return self.sink
    
    def get_source(self): 
        return self.source

    def get_unit_loads(self): 
        if self.max_priority > 0:
            return False
        return self.unit_loads