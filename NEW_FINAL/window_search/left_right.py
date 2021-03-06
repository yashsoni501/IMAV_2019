from djitellopy import Tello
import cv2
import numpy as np
import time
import imutils as im

from window_search.align_rect import FrontEnd as align_rect

font = cv2.FONT_HERSHEY_COMPLEX

class FrontEnd(object):

    def __init__(self,tello):
        self.tello = tello
        # self.tello = Tello()

        # self.cap = cv2.VideoCapture(0)
        self.tracker = cv2.TrackerKCF_create()
        # self.tracker = cv2.CSRT_create()
        self.rcOut = np.zeros(4)
        self.bbox = (5,5,20,20)

        self.trigger = 0
        self.trigger_init = 0

        self.ar = 0

        self.ARmean = np.array([0])
        self.ARqueue = np.zeros((7,1))
        self.ARvar = np.array([0])

        self.lost = 0

        self.visible = 0 

        self.align_rect = align_rect(self.tello)

    def run(self,right):

        frame_read = self.tello.get_frame_read()

        should_stop = False

        while not should_stop:
            frame = frame_read.frame
            print(self.tello.get_bat())
            if frame_read.stopped:
                frame_read.stop()
                break
            cv2.imshow("original",frame)

            key = cv2.waitKey(1) & 0xFF;
            
            if (1):                                                           # to update automate
                dst,mask = self.preproccessAndKey(frame)                                    # to update
                rect = self.get_coordinates(mask,dst)                                       # to update
                if(self.trigger_init==0):                    
                    if(rect[0][0] == 0):
                        print("rectangle pehle nhi mila")
                        continue
                    else:
                        print("hahahah")
                        self.trigger_init = 1

                print(self.trigger_init)

             # dikha toh uske saamne align kra, ho gya to tracking wala part start kr dia.

                if self.trigger_init == 1:  # now align in front

                    # self.align_rect.run()
                    print("align ho gya hai ab toh")
                    self.trigger_init = 2
                    # self.align_rect.clear()
                    time.sleep(0.1)


                if self.trigger_init == 2:  # now start tracking
                    # cv2.rectangle(dst,int(rect[0]),int(rect[2]),(255,255,255),3)
                    print(rect)

                    ok = self.start_tracking(rect,dst)
                    self.visible = 0
                    # print("gsfchdjkxnjdfbhghujsndnfvghujkddfguhxijkdc dsvcjndfvdhbj  :: {}".format(ok))
                    print("Now have started tracking")
                    # time.sleep(0.1)
                    if (ok == True):
                        self.trigger_init = 3
                    else:
                        continue

                if self.trigger_init == 3:   # now update tracking
            
                    self.track(dst)
                    print("Still Tracking")
                    if self.trigger == 1:
                        self.trigger_init = 4
                        self.trigger = 0

                if self.trigger_init == 4:
                    rect = self.get_coordinates(mask,dst)
                    print("searching for new rectangle now")
                    if(rect[0][0] == 0):
                        self.rcOut[0] = -20           #updated the velocity
                        self.rcOut[1] = 0
                        self.rcOut[2] = 0
                        self.rcOut[3] = 0
                    else:
                        print("ahhhahahah")
                        self.trigger_init = 5

                if self.trigger_init == 5:
                    print("ab phirse align kro")
                    # self.align_rect.run()
                    right = right + 1
                    should_stop = True
                    self.rcOut = [0,0,0,0]
                    # self.align_rect.clear()
                    return right

            else:
                self.manualRcControl(key)

            self.sendRcControl()

    def clear(self):
        
        self.tracker = cv2.TrackerKCF_create()
        # self.tracker = cv2.CSRT_create()
        self.rcOut = np.zeros(4)
        self.bbox = (5,5,20,20)

        self.trigger = 0
        self.trigger_init = 0

        self.ar = 0

        self.ARmean = np.array([0])
        self.ARqueue = np.zeros((7,1))
        self.ARvar = np.array([0])

        self.lost = 0      


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
        elif key == ord("l"):
            self.tello.land()
        elif key == ord("t"):
            try:
                self.tello.takeoff()
            except:
                print("takeoff toh ho gya lol")
            time.sleep(2)
        else:
            self.rcOut = [0,0,0,0]
        return

    def sendRcControl(self):
        self.tello.send_rc_control(int(self.rcOut[0]),int(self.rcOut[1]),int(self.rcOut[2]),int(self.rcOut[3]))
        self.rcOut = [0,0,0,0]

        return

    def preproccessAndKey(self,frame_read):

        frameBGR = frame_read
        frame2use = im.resize(frameBGR,width=720)
            
        frame = frame2use 
        
        dst = frame2use            
        mask = self.getRectMask(dst)

        return dst,mask


    def getRectMask(self,frame):

        kernel = np.ones((5,5),np.uint8)#param 1

        blurred = cv2.GaussianBlur(frame, (7, 7), 0)#param 1

        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        h,s,v = cv2.split(hsv)

        dilS = cv2.dilate(s,kernel,iterations = 1)
        newS = dilS-s
        newS = cv2.equalizeHist(newS)
        # newS = cv2.GaussianBlur(newS, (11, 11), 0)


        dilV = cv2.dilate(v,kernel,iterations = 1)#param 1
        newV = dilV-v
        newV = cv2.equalizeHist(newV)

        dilH = cv2.dilate(h,kernel,iterations = 1)
        newH = dilH-h
        newH = cv2.equalizeHist(newH)


        sabKaAnd = cv2.bitwise_or(newS,newV)
        kernel2 = np.ones((3,3),np.uint8)#param 1
        sabKaAnd = cv2.erode(sabKaAnd,kernel2,iterations = 1)#param 1
        sabKaAnd = cv2.erode(sabKaAnd,kernel2,iterations = 1)#param 1

        sabKaAnd = cv2.dilate(sabKaAnd,kernel2,iterations = 1)#param 1
        sabKaAnd = cv2.GaussianBlur(sabKaAnd, (11, 11), 0)

        maskSab = cv2.inRange(sabKaAnd,120,255)#param 1****

        maskSab = cv2.erode(maskSab,kernel2,iterations = 1)
        maskSab = cv2.dilate(maskSab,kernel2,iterations = 1)

        maskSab = cv2.bitwise_and(maskSab,newV)
        maskSab = cv2.equalizeHist(maskSab)
        maskSab = cv2.inRange(maskSab,190,255)# param *****

        kernel2 = np.ones((2,2),np.uint8) #param ****
        maskSab = cv2.erode(maskSab,kernel2,iterations = 1)
        maskSab = cv2.dilate(maskSab,kernel2,iterations = 1)

        return maskSab

    # def getRectMask(self,frame):

    #     hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    #     # define range of blue color in HSV
    #     lower_blue = np.array([98,79,78])
    #     upper_blue = np.array([128,245,169])

    #     # Threshold the HSV image to get only blue colors
    #     mask = cv2.inRange(hsv, lower_blue, upper_blue)
    #     cv2.imshow("mask",mask)

    #     return mask



    def order_points(self, pts):

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


    def get_coordinates(self, mask,frame):

        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        rect = np.zeros((4,2), dtype ="float32")
        oldArea = 300
        for cnt in contours:
            area = cv2.contourArea(cnt)
            approx = cv2.approxPolyDP(cnt, 0.012*cv2.arcLength(cnt, True), True) # 0.012 param
            x = approx.ravel()[0]
            y = approx.ravel()[1]
            arSet = 0.15  #change krde for different sizes
            if area > 300:#param

                if len(approx) == 4:
                    ar = (np.linalg.norm(approx[0] - approx[1]) + np.linalg.norm(approx[2] - approx[3]))/(np.linalg.norm(approx[2]-approx[1])+np.linalg.norm(approx[0]-approx[3]))
                    if ar > 1:
                        ar=1/ar

                    hull = cv2.convexHull(cnt)
                    hull_area = cv2.contourArea(hull)
                    solidity = float(area)/hull_area

                    condition = ar < 0.4 and ar > 0.25 #change for different rrect size
                    if solidity > 0.95 and condition:

                        self.ar = ar
                        # print "ar",self.ar

                        self.ARqueue = np.roll(self.ARqueue,1,axis = 0)
                        self.ARqueue[0,:] = [ar]

                        self.ARvar = np.var(self.ARqueue,axis=0)
                        self.ARmean = np.mean(self.ARqueue,axis = 0)

                        if area > oldArea:
                            cv2.drawContours(frame, [approx], 0, (0, 0, 0), 5)
                            #cv2.circle(frame,(int(cx),int(cy)), 3, (0,0,255), -1)
                            cv2.putText(frame, "Rectangle", (x, y), font, 1, (0, 0, 0))

                            cntMain = approx
                            rect = self.order_points(cntMain)
                            # print("reached here")

                            oldArea = area

        return rect

    def start_tracking(self, rect,frame):

        self.bbox = (rect[0][0],rect[0][1],rect[2][0]-rect[0][0],rect[2][1]-rect[0][1])
        # print("self.bbox is :: :: {}".format(self.bbox))
        # cv2.imshow("frame is",frame)
        self.tracker = cv2.TrackerKCF_create()
        ok = self.tracker.init(frame,self.bbox)
        # print("Val of OK inside start is {}".format(ok))
        # p1 = (int(self.bbox[0]), int(self.bbox[1]))
        # p2 = (int(self.bbox[0]+ self.bbox[2]), int(self.bbox[1]+self.bbox[3]))
        # cv2.rectangle(frame, p1, p2, (255,255,255), 2, 1)
        # cv2.imshow("with frame",frame)
        # cv2.waitKey(20)
        return ok

    def track(self,frame):

        ok, self.bbox = self.tracker.update(frame)

        if ok:
            p1 = (int(self.bbox[0]), int(self.bbox[1]))
            p2 = (int(self.bbox[0]+ self.bbox[2]), int(self.bbox[1]+self.bbox[3]))
            cv2.rectangle(frame, p1, p2, (255,0,0), 2, 1)
            cv2.imshow("with frame",frame)
            print("still visible")
            self.rcOut[0] = -20                #changed
            self.rcOut[1] = 0
            self.rcOut[2] = 0
            self.rcOut[3] = 0
            self.trigger = 0
            self.visible += 1
            self.lost = 0

        else:
            if(self.visible<5):
                self.trigger_init = 2
                return
            print("LOST")
            self.visible = 0
            # self.lost +=1
            # if(self.lost>10):
            self.trigger = 1

def main():
    tello = Tello()
    tello.connect()
    tello.streamoff()
    tello.streamon()
    frontend = FrontEnd(tello)
    right = 0
    while(right<2):
        right = frontend.run(right)
        print("right is now hsdawqbvqwuja : {}".format(right))
        frontend.clear()

    print("found the end of the code")
    tello.land()
    tello.end()

if __name__ == '__main__':
    main()