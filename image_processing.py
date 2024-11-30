import cv2
import numpy as np
import os
import logging
import math
import io
logger = logging.getLogger(__name__)
def getfileext(filename):
    parts = filename.split('.')
    ext = parts[-1]
    return "." + ext

def newfilename(filename, postfix):
    ext = getfileext(filename)
    stopspot = len(filename) - len(ext)
    left_side = filename[:stopspot]
    return left_side + postfix + ext

def size_image(file, filename, in_width, in_height, postfix):
    # expecting stream from request form file
    #working for PNG Files...
    #fails for GIFS
    stream = io.BytesIO(file.read())
    stream.seek(0)
    np_array = np.frombuffer(stream.read(), dtype=np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    #img =  cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    orig_height,orig_width = img.shape[:2]
    #img = Image.fromarray(img)
    #Do the math to scale down
    scale = min(in_width/orig_width,in_height/orig_height)
    new_height = math.ceil(int(scale*orig_height))
    new_width = math.ceil(int(scale*orig_width))
    new_img = cv2.resize(img,(new_width,new_height))
    new_file_name = newfilename(filename, postfix)
    #cv2.imwrite(new_file_name,new_img)
    success, encoded = cv2.imencode(getfileext(filename), new_img)
    encoded_io = io.BytesIO(encoded.tobytes())
    return encoded_io, new_file_name



def mobile_size_image(file, filename):
    width = 1000
    height = 500
    ext = getfileext(filename)
    if ext != ".gif":
        return size_image(file, filename,width,height,"_mobile")
    else:
        return file,filename
def discord_size_image(file, filename):
    width = 500
    height = 500
    ext = getfileext(filename)
    if ext != ".gif":
        return size_image(file, filename,width,height,"_discord")
    else:
        return file, filename

def remove_metadata_image(file, filename):
    ext = getfileext(filename)
    if ext != ".gif":
        img = cv2.imread(filename)
        orig_height,orig_width = img.shape[:2]
        return size_image(filename,orig_height,orig_width,"")
    else:
        return file, filename



