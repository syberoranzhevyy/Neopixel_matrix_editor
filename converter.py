import os, json
from matplotlib.colors import to_hex, to_rgb, to_rgba

def convert_rgb_to_hex(rgb_col):
    hex_col = hex(int(to_hex(rgb_col, keep_alpha=False).replace('#','0x'),16))
    #print('convert rgb to hex ', rgb_col, ' >> ', hex_col)
    return hex_col

readpath = './ledfile/'
savepath = './conv_ledfile/'

if not os.path.isdir(savepath):
    os.mkdir(savepath)

for file in os.listdir(readpath):
    if '.led' in file:
        with open(readpath + file, 'r') as ledfile:
            ledmovie = json.load(ledfile)

        if 'bright' in ledmovie.keys():
            conv_string = 'b-' + str(ledmovie['bright'])
        else:
            conv_string = 'b-0.6'
        for pic in ledmovie['picture_list']:
            for led in pic['picture']:
                if isinstance(led[1], str):
                    col = led[1]
                elif isinstance(led[1], list):
                    col = convert_rgb_to_hex(led[1])
                conv_string += '\np-'+ str(led[0]) + '-' + col
            conv_string += '\nd-' + str(pic['delay'])

        with open(savepath + file, 'w') as convfile:
            convfile.write(conv_string)
        
