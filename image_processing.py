import cv2
import numpy as np
import os
import logging
import math
import ffmpeg
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

#def convert_mov_to_mp4(file, filename):

def convert_mov_to_mp4_old(file, filename):
       # Save the input MOV stream to a temporary file
    stream = io.BytesIO(file.read())
    stream.seek(0)
    with open('temp_input.mov', 'wb') as f:
        f.write(stream.read())

    # Create a BytesIO stream for the output MP4
    output_mp4_stream = io.BytesIO()

    # Use ffmpeg to remux the MOV to MP4
    try:
        (
            ffmpeg
            .input('temp_input.mov')
            .output('temp_output.mp4', vcodec='libx264', acodec='aac')  # Copy video and audio streams without re-encoding
            .run(quiet=True, overwrite_output=True)
        )

        # Read the output MP4 into a BytesIO stream
        with open('temp_output.mp4', 'rb') as f:
            output_mp4_stream.write(f.read())

        # Reset the stream's position to the beginning
        output_mp4_stream.seek(0)

        #cleanup temp files
        if os.path.exists('temp_input.mov'):
            os.remove('temp_input.mov')
        if os.path.exists('temp_output.mp4'):
            os.remove('temp_output.mp4')

    except ffmpeg.Error as e:
        print(f"Error during remuxing: {e}")
        raise

    oldfileparts = filename.split(".")
    filestart = oldfileparts[0]
    newFilename = filestart + '.mp4'

    return output_mp4_stream, newFilename