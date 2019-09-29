import sys
if '/opt/ros/kinetic/lib/python2.7/dist-packages' in sys.path:
	sys.path.remove('/opt/ros/kinetic/lib/python2.7/dist-packages')
from djitellopy import Tello
import cv2
import numpy as np
import time
import imutils as im

import sys
import os

import threading

sys.path.append(os.path.abspath("./start_to_next"))
from main import starting 
sys.path.remove(os.path.abspath("./start_to_next"))

sys.path.append(os.path.abspath("./warehouse"))
from class_call import warehouse_overall 
sys.path.remove(os.path.abspath("./warehouse"))

sys.path.append(os.path.abspath("./window_search"))
from main_test import starting as rect_pass
sys.path.remove(os.path.abspath("./window_search"))

sys.path.append(os.path.abspath("./JoyStick_Controller"))
from controller_module import Controller
import xbox

sys.path.remove(os.path.abspath("./JoyStick_Controller"))

from after_shelf import FrontEnd as after

from orient_yaw import Orient as orient

Out_of_bounds = False

class hoohah(object):

    def __init__(self,tello):

        self.tello = tello

        self.starting = starting(self.tello)

        self.initial_yaw = self.tello.get_yaw()


        self.warehouse = warehouse_overall(self.tello)

        self.rect_pass = rect_pass(self.tello)

        self.after = after(self.tello)

        self.orient = orient(self.tello)

    def run(self):
        trig = 0

        try:
            self.tello.takeoff()
        except:
            print("Ab toh takeoff ho gya lol")
            
        
        time.sleep(2)


        print("Starting Controller")
        try:
            self.joy = xbox.Joystick()

            self.controller = Controller(self.tello, self.joy)
            x = threading.Thread(target=self.controller.run, daemon=True)
            x.start()
        except:
            print("Control fail ho gya lol")

        # self.starting.run(self.initial_yaw)										#uncomment this VERY IMPORTANT!!!!! 	

        yaw = self.tello.get_yaw()

        self.warehouse.algo(yaw)

        self.orient.orient(yaw)

        self.warehouse.clear()

        self.tello.move_right(40)													# to update

        print("have moved right")

        while(trig == 0):

            up, left, trig = self.rect_pass.run(yaw)
            print("up = {}, left = {}, trig = {}".format(up,left,trig))

            self.after.run(left,up,yaw)

        trig = 0



        # print("now going for after run")

        # self.after.run(2,0,yaw)


        # 3,0,yaw

        self.warehouse.algo(yaw)

        self.orient.orient(yaw)

        self.warehouse.clear()

        while(trig == 0):

            up, left, trig = self.rect_pass.run(yaw)

        # self.after.run(left,up,yaw)

        self.tello.land()
        self.tello.end()
        print("Ended")


def main():
    print("now i am gonna start the mission")
    tello = Tello()
    tello.connect()
    tello.streamoff()
    tello.streamon()
    start = hoohah(tello)
    start.run()
    # print("UP is {} and right is {}".format(a,b))

if __name__ == '__main__':
    main()

