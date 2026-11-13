"""One constant music gain shared by browser playback and exported composition."""
import math

def music_gain(value=1):
 if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:
  raise ValueError('musicGain must be a finite number from 0 to 1')
 return float(value)
