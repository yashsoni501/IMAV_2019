def order_points(pts):

    pts = pts.reshape(4,2)
    # initialzie a list of coordinates that will be ordered
    # such that the first entry in the list is the top-left,
    # the second entry is the top-right, the third is the
    # bottom-right, and the fourth is the bottom-left
    rect = np.zeros((4, 2), dtype = "float32")
 
    # the top-left point will have the smallest sum, whereas
    # the bottom-right point will have the largest sum
    s = pts.sum(axis = 1)
    # print "dim",pts.shape
    # print "s",s 
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
 
    # now, compute the difference between the points, the
    # top-right point will have the smallest difference,
    # whereas the bottom-left will have the largest difference
    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
 
    # return the ordered coordinates
    return rect

from djitellopy import Tello
import cv2
import pygame
from pygame.locals import *
import numpy as np
import time
import imutils as im
import tello_frame_detection

# Speed of the drone
S = 60
# Frames per second of the pygame window display
FPS = 25

font = cv2.FONT_HERSHEY_COMPLEX


class FrontEnd(object):
    """ Maintains the Tello display and moves it through the keyboard keys.
        Press escape key to quit.
        The controls are:
            - T: Takeoff
            - L: Land
            - Arrow keys: Forward, backward, left and right.
            - A and D: Counter clockwise and clockwise rotations
            - W and S: Up and down.
    """

    def __init__(self):
        # Init pygame
        # Init Tello object that interacts with the Tello drone
        self.tello = Tello()
        self.telloEulerAngles = np.zeros((1,3))

        self.rcOut=np.zeros(4)
        
        self.R = np.zeros((3,3))
        self.PoseFlag = 1
        self.telloPose = np.zeros((1,3))
        self.poseQueue = np.zeros((7,3))
        self.telloPoseVariance = np.zeros(3)
        self.telloPoseMean = np.zeros(3)
        self.telloPoseMean15 = np.zeros(3)
        
        self.cntErNrm = 0
        self.cntError = np.array([0,0,0])
        
        self.tello.TIME_BTW_RC_CONTROL_COMMANDS = 20

        self.frameCenter = np.zeros((1,2))


        # variables for shelf passing
        self.trigger = 0
        self.lastValue = 0
        self.flag1 = 1
        self.distanceFrmRect = 0
        self.apprchFlowFlag =0
        self.passFromWindowModSccss = 0

        #variables for aligning with the window
        self.alnFlowFlag = 0

        # self.telloPose = np.array([])
            # self.telloEulerAngles = EulerAngles

    def run(self):

        if not self.tello.connect():
            print("Tello not connected")
            return

        # In case streaming is on. This happens when we quit this program without the escape key.
        if not self.tello.streamoff():
            print("Could not stop video stream")
            return

        if not self.tello.streamon():
            print("Could not start video stream")
            return

        frame_read = self.tello.get_frame_read()

        should_stop = False

        Height = 100
        while not should_stop:
            if frame_read.stopped:
                frame_read.stop()
                break
            dst = self.preproccessAndKey(frame_read)
            rect, ctlist = tello_frame_detection.get_cnt(dst)
            if not rect is None:
                cv2.drawContours(dst, [rect], -1, (0,255,0), 3)

            cv2.imshow("rectified",dst) 

            key = cv2.waitKey(1) & 0xFF;

            trigger = self.stateTrigger(key,"p")
            self.manualRcControl(key)

            if not rect is None:
                f=self.passFromWindow(trigger,key,rect,dst)
            #cv2.drawContours(dst, ctlist, -1, (255,255,0), 3)
            

            self.sendRcControl() 
            
            

            if key == ord("q"):
                break
            if key == ord("t"):
                try:
                    self.tello.takeoff()    
                except:
                    pass
            if key == ord("l"):
                self.tello.land()
                Height = 100

            if key == ord('q'):
                break

            time.sleep(1 / FPS)

        # Call it always before finishing. I deallocate resources.
        self.tello.end()

    def preproccessAndKey(self,frame_read):
        frameBGR = np.copy(frame_read.frame)
        frame2use = im.resize(frameBGR,width=720)
            
        frame = frame2use 


        dst = self.rectifyInputImage(frame2use)          

        return dst

    def stateTrigger(self,key,char):
        if key == ord(char):
            value = 1
        else:
            value = 0

        trigger = value - self.lastValue
        self.lastValue = value

        return trigger 
        
    def algnToFrame(self,key):
        print ("key",key,"Flag",self.alnFlowFlag)
        if key == ord("o"):
            self.alnFlowFlag = 1
            self.cntErNrm = 0
            
        if self.alnFlowFlag == 1:
            if self.cntErNrm > 10 or self.cntErNrm ==0:
                print ("Norm ",self.cntErNrm)
                Pose = self.telloPoseMean
                self.PoseController(key,Pose[0],0,0,0.38)
                self.alnFlowFlag = 1
            else:
                self.alnFlowFlag = 0
        else:
            self.manualRcControl(key)
            pass

    def passFromWindow(self,trigger,key,rect,dst):
        frameH,frameW = 20,75
        self.PoseEstimationfrmCnt(rect,dst,frameH,frameW)
        #self.manualRcControl(key)
        self.algnToFrame(key)
        self.babyStepForward(trigger,key)
        result = self.passFromWindowModSccss
        return result

    def babyStepForward(self,trigger,key):
        
        # if trigger == 1:
        if trigger == 1:
            Pose = self.telloPoseMean
            if Pose[0] >450:
                self.distanceFrmRect = 450
            else: 
                self.distanceFrmRect = Pose[0]

            self.apprchFlowFlag = 1
            self.cntErNrm = 0
        
        
        if self.telloPoseMean[0] < 170 and self.telloPoseMean[0] != 0:
            if self.flag1 == 1:
                startTime = time.time()
                self.flag1 = 0
            else: 
                startTime = 0
            eTime =  time.time() - startTime
            
            if eTime < 10: # shoot time
            
                
                self.rcOut[0] = 0
                self.rcOut[1] = 0
                self.rcOut[2] = 0
                self.rcOut[3] = 0
                self.passFromWindowModSccss = 0
            elif eTime >10 :
                self.cntErNrm = 0
                self.apprchFlowFlag = 0
                self.passFromWindowModSccss = 1

            else: # shoot time
                self.rcOut[0] = 0
                self.rcOut[1] = 0
                self.rcOut[2] = 0
                self.rcOut[3] = 0
                # self.tello.move_forward(50)
                # time.sleep(5)
                self.cntErNrm = 0
                self.apprchFlowFlag = 0

                self.passFromWindowModSccss = 0
        else:
            self.passFromWindowModSccss = 0 

        if self.apprchFlowFlag == 1:
            if self.cntErNrm > 15 or self.cntErNrm ==0:
                print ("Norm ",self.cntErNrm)
               # print"Nua Nua Nua Nua"
                dist = self.distanceFrmRect
                stepLength = 30

                print ("dist",dist)

                self.PoseController(key,dist - stepLength ,0,0,0.35)
                self.apprchFlowFlag = 1
            else:
                self.apprchFlowFlag = 0

            if self.cntErNrm < 15 and self.cntErNrm >0:
                Pose = self.telloPoseMean
                self.distanceFrmRect = Pose[0]
                self.cntErNrm = 0    
        else:
            self.manualRcControl(key)
            pass



    def algnYawToFrame(self,key):
        pass
    def findMissingFrame(self,key):
        pass
    def shoot(self,key):
        pass

    def manualRcControl(self,key):
        if key == ord("w"):
            self.rcOut[1] = 50
        elif key == ord("a"):
            self.rcOut[0] = -50
        elif key == ord("s"):
            self.rcOut[1] = -50
        elif key == ord("d"):
            self.rcOut[0] = 50
        elif key == ord("u"):
            self.rcOut[2] = 50
        elif key == ord("j"):
            self.rcOut[2] = -50
        else:
            self.rcOut = [0,0,0,0]

        return

    def sendRcControl(self):
        print("rcOut", self.rcOut)
        self.tello.send_rc_control(int(self.rcOut[0]),int(self.rcOut[1]),int(self.rcOut[2]),int(self.rcOut[3]))
        self.rcOut = [0,0,0,0]

        return

    def rectifyInputImage(self,frame2use):

        K = np.array([[7.092159469231584126e+02,0.000000000000000000e+00,3.681653710406367850e+02],[0.000000000000000000e+00,7.102890453175559742e+02,2.497677007139825491e+02],[0.000000000000000000e+00,0.000000000000000000e+00,1.000000000000000000e+00]])
        dist = np.array([0,0,0,0,0])
        K_inv = np.linalg.inv(K)

        h , w = frame2use.shape[:2]

        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(K,dist,(w,h),1,(w,h))

        mapx,mapy = cv2.initUndistortRectifyMap(K,dist,None,newcameramtx,(w,h),5)
        dst = cv2.remap(frame2use,mapx,mapy,cv2.INTER_LINEAR)

        x,y,w,h = roi
        dst = dst[y:y+h,x:x+w]

        return dst

   
    def PoseEstimationfrmCnt(self,rect,frame,frameH,frameW):
        # Contours detection
        Pose = self.PoseEstimation(rect,frameH,frameW)
        if self.PoseFlag == 1:
            # print "PoseFlag",self.PoseFlag
            self.telloPose = np.transpose(Pose)

            self.poseQueue = np.roll(self.poseQueue,1,axis = 0)
            self.poseQueue[0,:] = [Pose[0,0],Pose[0,1],Pose[0,2]]

            self.telloPoseVariance = np.var(self.poseQueue,axis=0)
            self.telloPoseMean = np.mean(self.poseQueue,axis = 0)
            # print "PoseQueue",self.poseQueue
            print ("PoseMean",self.telloPoseMean)
            # print "telloPoseVariance" , self.telloPoseVariance
        else:
            pass

        varN = np.linalg.norm(self.telloPoseVariance)
                            # print "varN",varN
        # cv2.imshow("Frame", frame)
        # cv2.imshow("Mask", mask)

    

    def PoseEstimation(self,rect,frameH,frameW):

        K = np.array([[6.981060802052014651e+02,0.000000000000000000e+00,3.783628172155137577e+02],[0.000000000000000000e+00,6.932839845949604296e+02,2.823973488087042369e+02],[0.000000000000000000e+00,0.000000000000000000e+00,1.000000000000000000e+00]])
        # dist = np.array([-1.428750372096417864e-01,-3.544750945429044758e-02,1.403740315118516459e-03,-2.734988255518019593e-02,1.149084393996809700e-01])

        # K = np.array([[6.331284731799049723e+02,0.000000000000000000e+00,3.240546706735938187e+02],[0.000000000000000000e+00,6.276117931324869232e+02,2.404437048001034611e+02],[0.000000000000000000e+00,0.000000000000000000e+00,1.000000000000000000e+00]])
        K_inv = np.linalg.inv(K)
        crn = rect

        # print "crn",crn
        # crnVect = np.array([[crn[0]],[crn[1]],[1]])

        crnList = rect

        frameH = frameH/2 
        frameW = frameW/2

        src = np.array([[-1*frameH,-1*frameW],[frameH,-1*frameW],[frameH,frameW],[-1*frameH,frameW]])

        h, status = cv2.findHomography(src,crnList)

        det = np.linalg.det(h)

        if det != 0 :
            self.PoseFlag=1
            # print "PoseFlag flag changed"

            hInv = np.linalg.inv(h)

            h1h2h3 = np.matmul(K_inv,h)

            h1T = h1h2h3[:,0]
            h2T = h1h2h3[:,1]
            h3T = h1h2h3[:,2]
            

            h1Xh2T = np.cross(h1T,h2T)


            h1_h2_h1Xh2T = np.array([h1T,h2T,h1Xh2T])
            h1_h2_h1Xh2 = np.transpose(h1_h2_h1Xh2T)

            u, s, vh = np.linalg.svd(h1_h2_h1Xh2, full_matrices=True)

            uvh = np.matmul(u,vh)
            det_OF_uvh = np.linalg.det(uvh)

            M = np.array([[1,0,0],[0,1,0],[0,0,det_OF_uvh]])

            T = h3T/np.linalg.norm(h1T) # Translation Matrix
            T = T*100/17.5
            r = np.matmul(u,M)
            R = np.matmul(r,vh) # Rotation matrix
            T = T

            T_t = np.reshape(T,(3,1))
            neg_Rt_T = -1*np.dot(R.T,T_t)
            f = np.array([[0,0,0,1]])

            
            if neg_Rt_T[2,0] < 0:
                flag = -1
            else:
                flag = 1

            neg_Rt_T[2,0] = neg_Rt_T[2,0]*flag
            neg_Rt_T[0,0] = neg_Rt_T[0,0]*(-1)
            Pose = neg_Rt_T.T

            pX = Pose[0,0]
            pY = Pose[0,1]
            pZ = Pose[0,2]

            Pose[0,0] = pZ
            Pose[0,1] = -pX
            Pose[0,2] = -pY


        else:
            self.PoseFlag=0            
            Pose = np.array([[0,0,0]])

        return Pose


    def PoseController(self,key,xSetPt,ySetPt,zSetPt,kp):
        varN = np.linalg.norm(self.telloPoseVariance)
        # print "varN",varN
        Pose = self.telloPoseMean

        xEr = xSetPt - Pose[0]   
        yEr = ySetPt - Pose[1]
        zEr = zSetPt - Pose[2]

        self.cntError = np.array([xEr,yEr,zEr])
        norm = np.linalg.norm([xEr,yEr,zEr])
        self.cntErNrm = norm


        # if key == ord("e"): #press e to execute
        if True:
            if True: # put additional commands here
                
                MtnCmd = np.array([kp*xEr,kp*yEr,kp*zEr])

                MtnCmd[0] = -1*MtnCmd[0]
                self.rcOut = [MtnCmd[1], MtnCmd[0],MtnCmd[2],0]
                
                print( "HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

                if self.rcOut[0] > 35:
                    self.rcOut[0] = 35
                elif self.rcOut[0] < -35:
                    self.rcOut[0] = -35

                if self.rcOut[1] > 35:
                    self.rcOut[1] = 35
                elif self.rcOut[1] < -35:
                    self.rcOut[1] = -35

                if self.rcOut[2] > 35:
                    self.rcOut[2] = 35
                elif self.rcOut[2] < -35:
                    self.rcOut[2] = -35

                print("rcOut Inside", self.rcOut)

        else :
            self.manualRcControl(key)


def main():
    frontend = FrontEnd()

    # run frontend
    frontend.run()


if __name__ == '__main__':
    main()


            