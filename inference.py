import os
import shutil
import argparse
import sys
import patoolib
from pathlib import Path
from shutil import rmtree

import numpy as np
import matplotlib.pyplot as plt

from colorizator import MangaColorizator

def extract_cbr(file, out_dir):
    patoolib.extract_archive(file,  outdir = out_dir, verbosity = 1, interactive = False)

def create_cbz(file_path, files):
    patoolib.create_archive(file_path, files, verbosity = 1, interactive = False)
    
def subfolder_image_search(start_folder):
    return [x.as_posix() for x in Path(start_folder).rglob("*.[pPjJ][nNpP][gG]")]

def remove_folder(folder_path):
    rmtree(folder_path)

def process_image(image, colorizator, args):
    colorizator.set_image(image, args.size, args.denoiser, args.denoiser_sigma)
    return colorizator.colorize()

def colorize_single_image(image_path, save_path, colorizator, args):
    image = plt.imread(image_path)
    colorization = process_image(image, colorizator, args)
    plt.imsave(save_path, colorization)
    return True

def colorize_images(target_path, colorizator, args):
    images = [x.as_posix() for x in Path(args.path).rglob("*.[pPjJ][nNpP][gG]")]
    for image_path in images:
        save_path = os.path.join(target_path, os.path.basename(image_path))
        colorize_single_image(image_path, save_path, colorizator, args)

def colorize_cbr(file_path, colorizator, args):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    temp_path = 'temp_colorization'
    
    if os.path.exists(temp_path):
        remove_folder(temp_path)
    os.makedirs(temp_path)
    
    extract_cbr(file_path, temp_path)
    
    images = subfolder_image_search(temp_path)
    
    result_images = []
    for image_path in images:
        save_path = image_path
        
        path, ext = os.path.splitext(save_path)
        if (ext != '.png'):
            save_path = path + '.png'
        
        res_flag = colorize_single_image(image_path, save_path, colorizator, args)
        
        result_images.append(save_path if res_flag else image_path)
        
    
    result_name = os.path.join(os.path.dirname(file_path), file_name + '_colorized.cbz')
    
    create_cbz(result_name, result_images)
    
    remove_folder(temp_path)
    
    return result_name

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", required=True)
    parser.add_argument("-gen", "--generator", default = 'networks/generator.zip')
    parser.add_argument("-ext", "--extractor", default = 'networks/extractor.pth')
    parser.add_argument('-g', '--gpu', dest = 'gpu', action = 'store_true')
    parser.add_argument('-nd', '--no_denoise', dest = 'denoiser', action = 'store_false')
    parser.add_argument("-ds", "--denoiser_sigma", type = int, default = 25)
    parser.add_argument("-s", "--size", type = int, default = 576)
    parser.set_defaults(gpu = False)
    parser.set_defaults(denoiser = True)
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    if args.gpu:
        device = 'cuda'
    else:
        device = 'cpu'
    colorizer = MangaColorizator(device, args.generator, args.extractor)
    if os.path.isdir(args.path):
        colorization_path = os.path.join(args.path, 'colorization')
        if not os.path.exists(colorization_path):
            os.makedirs(colorization_path)
        colorize_images(colorization_path, colorizer, args)
    elif os.path.isfile(args.path):
        split = os.path.splitext(args.path)
        if split[1].lower() in ('.jpg', '.png', '.jpeg'):
            new_image_path = split[0] + '_colorized' + '.png'
            colorize_single_image(args.path, new_image_path, colorizer, args)
        elif split[1].lower() in ('.cbr'):
            colorize_cbr(args.path, colorizer, args)
        else:
            print('Wrong format')
    else:
        print('Wrong path')
