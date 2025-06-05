import numpy as np
import sys

class Sink():
    def __init__(self, x: int, y: int, state: np.ndarray, access_points: list):
        # position of the sink
        self.x = x
        self.y = y

        self.state = state
        self.width = state.shape[1]
        self.length = state.shape[0]

        if self.width > 1 or self.length > 1: 
            print("This version of the code can only handle a single 1x1 sink")
            sys.exit(1)

        if len(state.shape) == 2:
            self.height = 1
        else:
            self.height = state.shape[2]
        self.access_points = access_points
        self.virtual_lanes = None

    def __str__(self):
        return '{0}x{1} Sink at row {2}, column {3}, access_points {4}'.format(
            self.width, self.length, self.y, self.x, [point.ap_id for point in self.access_points]
        )

    def to_data_dict(self):
        data = dict()
        data['x'] = self.x
        data['y'] = self.y
        data['width'] = self.width
        data['length'] = self.length
        data['access_directions'] = list({point.direction for point in self.access_points})
        data['access_point_ids'] = [point.ap_id for point in self.access_points]
        return data

    def get_id(self):
        return str(self)