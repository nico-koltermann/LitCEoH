import shutil

import numpy as np
import random
import time

from .eoh_interface_EC import InterfaceEC
from solver.ceoh.utils.visualizeResults import *
from solver.ceoh.utils.visualizePromptFrequency import *

# main class for eoh
class EOH:

    # initilization
    def __init__(self, paras, problem, select, idea_select, manage, **kwargs):

        self.paras = paras

        self.prob = problem
        self.select = select
        self.idea_select = idea_select
        self.manage = manage

        # LLM settings
        self.use_local_llm = paras.llm_use_local
        self.llm_local_url = paras.llm_local_url
        self.api_endpoint = paras.llm_api_endpoint  # currently only API2D + GPT
        self.api_key = paras.llm_api_key
        self.llm_model = paras.llm_model
        self.llm_temperature = paras.llm_temperature

        # ------------------ RZ: use local LLM ------------------
        # self.use_local_llm = kwargs.get('use_local_llm', False)
        # assert isinstance(self.use_local_llm, bool)
        # if self.use_local_llm:
        #     assert 'url' in kwargs, 'The keyword "url" should be provided when use_local_llm is True.'
        #     assert isinstance(kwargs.get('url'), str)
        #     self.url = kwargs.get('url')
        # -------------------------------------------------------

        # Experimental settings
        self.pop_size = paras.ec_pop_size  # population size, i.e., the number of algorithms in population
        self.n_pop = paras.ec_n_pop  # number of populations

        self.operators = paras.ec_operators
        self.operator_weights = paras.ec_operator_weights
        if paras.ec_m > self.pop_size or paras.ec_m == 1:
            print("m should not be larger than pop size or smaller than 2, adjust it to m=2")
            paras.ec_m = 2
        self.m = paras.ec_m

        self.debug_mode = paras.exp_debug_mode  # if debug
        self.ndelay = 1  # default

        self.use_seed = paras.exp_use_seed
        self.seed_path = paras.exp_seed_path
        self.load_pop = paras.exp_use_continue
        self.load_pop_path = paras.exp_continue_path
        self.load_pop_id = paras.exp_continue_pop_nr
        self.exp_continue_folder = paras.exp_continue_folder

        self.output_path = paras.exp_output_path

        try:
            self.result_folder_name = os.environ["CURRENT_EXPERIMENT"]
        except:
            self.result_folder_name = None

        self.exp_n_proc = paras.exp_n_proc
        
        self.timeout = paras.eva_timeout

        self.use_numba = paras.eva_numba_decorator

        self.llm_url_info = paras.llm_url_info

        # Use Context with EoH
        self.use_example = paras.ec_use_example

        # Parameter for Ideas integration
        self.ideas_iteration_start = paras.ideas_iteration_start
        self.injection_loops = paras.injection_loops

        print("- EoH parameters loaded -")

        # Set a random seed
        random.seed(2024)

    # add new individual to population
    def add2pop(self, population, offspring):
        for off in offspring:
            for ind in population:
                if ind['objective'] == off['objective']:
                    if (self.debug_mode):
                        print("duplicated result, retrying ... ")
            population.append(off)

    def copy_files(self):
        """
        Copies JSON files from subdirectories if their generation number is
        less than or equal to `self.load_pop_id`.
        """
        base_path = os.path.join(self.output_path, self.exp_continue_folder)
        target_path = self.result_folder_name
        subfolders = ["pops", "pops_best", "all_programs"]

        for subfolder in subfolders:
            source_dir = os.path.join(base_path, subfolder)
            dest_dir = os.path.join(target_path, subfolder)

            os.makedirs(dest_dir, exist_ok=True)  # Ensure destination exists

            for filename in os.listdir(source_dir):
                if filename.endswith(".json"):
                    try:
                        # Extract generation number based on naming pattern
                        gen_index = -1 if subfolder in ["pops", "pops_best"] else 2
                        gen = int(filename.split("_")[gen_index].split(".")[0])

                        if gen <= int(self.load_pop_id):
                            shutil.copy(os.path.join(source_dir, filename), os.path.join(dest_dir, filename))
                    except (ValueError, IndexError):
                        print(f"Skipping file with unexpected format: {filename}")




    # run eoh
    def run(self):

        print("- Evolution Start -")

        time_start = time.time()

        # interface for evaluation
        interface_prob = self.prob

        # interface for ec operators
        interface_ec = InterfaceEC(self.paras, interface_prob, self.select, self.idea_select)

        # initialization
        population = []
        if self.use_seed:
            with open(self.seed_path) as file:
                data = json.load(file)
            population = interface_ec.population_generation_seed(data,self.exp_n_proc)
            filename = self.result_folder_name + "/pops/population_generation_0.json"
            with open(filename, 'w+') as f:
                json.dump(population, f, indent=5)
            n_start = 0
        else:
            if self.load_pop:  # load population from files
                print("load initial population from " + self.load_pop_path)
                with open(self.load_pop_path) as file:
                    data = json.load(file)
                for individual in data:
                    population.append(individual)
                print("initial population has been loaded!")

                n_start = int(self.load_pop_id) + 1

                # copy all files from the previous experiment
                self.copy_files()

            else:  # create new population
                print("creating initial population:")
                population = interface_ec.population_generation()
                population = self.manage.population_management(population, self.pop_size)

                print(f"Pop initial: ")
                for off in population:
                    print(" Obj: ", off['objective'], end="|")
                print()
                print("initial population has been created!")
                # Save population to a file
                filename = self.result_folder_name + "/pops/population_generation_0.json"
                with open(filename, 'w+') as f:
                    json.dump(population, f, indent=5)
                n_start = 0

        # main loop
        n_op = len(self.operators)

        for pop in range(n_start, n_start + self.n_pop, 1):
            print(pop)

            enable_idea_operator = pop < n_start + self.injection_loops
            use_idea_in_current_pop = self.ideas_iteration_start < pop

            if use_idea_in_current_pop and enable_idea_operator:
                for i in range(n_op):
                    print("Paper idea extraction.")
                    op = "p1"
                    parents, offsprings = interface_ec.get_algorithm(population, op, pop)
                    self.add2pop(population, offsprings)
                    size_act = min(len(population), self.pop_size)
                    population = self.manage.population_management(population, size_act)
                    print()

            else:
                for i in range(n_op):
                    op = self.operators[i]
                    print(f" OP: {op}, [{i + 1} / {n_op}] ", end="| \n")
                    op_w = self.operator_weights[i]
                    if (np.random.rand() < op_w):
                        parents, offsprings = interface_ec.get_algorithm(population, op, pop)
                    self.add2pop(population, offsprings)  # Check duplication, and add the new offspring
                    for off in offsprings:
                        print(" Obj: ", off['objective'], end="|")

                    size_act = min(len(population), self.pop_size)
                    population = self.manage.population_management(population, size_act)
                    print()


            # Save population to a file
            filename = self.result_folder_name + "/pops/population_generation_" + str(pop + 1) + ".json"
            with open(filename, 'w+') as f:
                json.dump(population, f, indent=5)

            # Save the best one to a file
            filename = self.result_folder_name + "/pops_best/population_generation_" + str(pop + 1) + ".json"
            with open(filename, 'w+') as f:
                json.dump(population[0], f, indent=5)


            print(f"--- {pop + 1} of {self.n_pop} populations finished. Time Cost:  {((time.time()-time_start)/60):.1f} m")
            print("Pop Objs: ", end=" ")
            for i in range(len(population)):
                print(str(population[i]['objective']) + " ", end="")
            print()
            try:
                load_and_plot_objective_ranges(self.result_folder_name)
            except Exception as e:
                print(f"Error plotting objective ranges: {e}")
            try:
                plot_evaluation_time(self.result_folder_name)
            except Exception as e:
                print(f"Error plotting evaluation time: {e}")

