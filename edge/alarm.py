'''Per camera-alarm state; streaming version of figlib_eval's M-K rule 
'''

from collections import deque 
from dataclasses import dataclass, field 

@dataclass
class CameraAlarm: 
    '''Rolling Window of M-K state for single camera
    Armed flag means a plume thats their for 40 minutes raises ONE alarm not 40'''

    threshold: float
    K: int
    M: int 
    _window: deque = field(init=False) # rolling confidence window, creates deque itself later
    _armed: bool = field(init=False, default=True) # is camera allowed to generate a new alarm 

    def __post_init__(self): # handles anything that requires logic, functions in this case its the deque 
        if not 1 <= self.K <= self.M: # makes sure lowest value of K and M is 1 and K fits in the window of M 
            raise ValueError(f'need 1 <= K <= M, got K={self.K} M={self.M}')
        self._window = deque(maxlen=self.M) # creates the rolling window 

        @property  # turns method into an acessible attribute
        def hot(self) -> bool: 
            '''at least K of the last M frames at or above threshold'''
            return sum(1 for c in self._window if c >= self.threshold) >= self.K 
        # for every confidence in the threshold how many True values are there: True = conf's in M window being over Thresh and if thats more than or equal to K it fires to be counted as an alarm 

        def update(self, conf: float) -> bool: # camera new conf score is it a NEW alarm or not
            '''Gives the camera one new confidence score 
            Returns True on a NEW alarm 
             True the first frame it goes hot then False while it stays hot then rearms'''
            self._window.append(conf) # feeds new frame into the window 
            if self.hot: # is cam hot, so are there enough K 
                if self._armed: # are we ready to report  (CAMERA IS HOT)
                    self._armed = False # disarms it if its been reported for the upcoming windows
                    return True # after disarming it triggers the alarm 
                return False # This is another frame of the same ongoing hot event which we already alreted do not trigger another alarm 
            # prevents one alarm per frame 
            else: # if cam is not hot then reset the alarm so we can trigger it when we get another alert 
                self._armed = True  
                return False # no alarm is getting sent on this cold frame 

        def reset(self): # defines the reset operation
            '''Used when camera goes offline and comes back 
            Kind of like clearing History'''
            self._window.clear() # deleted everything stored in _window
            self._armed = True # rearms the camera 

class AlarmBank: 
    '''One camera alarm per cam created on the first sight
    remember the alarm state of each cam seperately'''   
    def __init__(self, threshold: float, K: int, M: int):
        self.threshold = threshold
        self.K = K 
        self.M = M
        self._cams: dict[str, CameraAlarm] = {} # creates cam dict with cam names(str) as keys and CamAlarm objects as values  

    def update(self, camera: str, conf: float) -> bool: # called when new cam conf comes in 
        if camera not in self._cams: # checks in dict if we have seen the cam 
            self._cams[camera] = CameraAlarm(self.threshold, self.K, self.M) 
            # creates CameraAlarm for that cam if we dont have one yet 
        return self._cams[camera].update(conf) #updates cam w new confidence 

    def hot_cameras(self) -> list[str]: # gives names of call cams currenlty hot 
        return [c for c, a in self._cams.items() if a.hot] # returns them as a list of str

    def reset(self, camera: str): # finds which camera to reset
        if camera in self._cams: # do we cam CameraAlarm for this camera 
            self._cams[camera].reset() # resets that camera so it becomes armed again 