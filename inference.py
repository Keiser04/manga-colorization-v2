import os
import shutil
import argparse
import sys
import patoolib
from pathlib import Path
from shutil import rmtree
import time

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

from colorizator import MangaColorizator

def convert_to_bw(img_path):
    color_image = Image.open(img_path)
    bw = color_image.convert('L')
    bw.save(img_path)

def convert_webp_to_png(img_path, temp_folder):
    if img_path.lower().endswith('.webp'):
        img = Image.open(img_path)
        png_path = os.path.join(temp_folder, os.path.basename(img_path)[:-5] + '.png')
        img.save(png_path, 'PNG')
        return png_path
    return img_path

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
    start_time = time.time()
    temp_path = os.path.join('temp_colorization', os.path.basename(image_path))
    shutil.copy2(image_path, temp_path)
    temp_path = convert_webp_to_png(temp_path, 'temp_colorization')
    convert_to_bw(temp_path)

    try:
        # Abre la imagen con PIL, que puede manejar varios formatos de imagen
        image = Image.open(temp_path)
        # Guarda la imagen como PNG
        image.save(temp_path, 'PNG')
        # Ahora puedes abrir la imagen como PNG
        image = plt.imread(temp_path)
    except Exception as e:
        print(f"Error al abrir/guardar la imagen {temp_path}: {str(e)}")
        return False

    colorization = process_image(image, colorizator, args)
    plt.imsave(save_path, colorization)
    os.remove(temp_path)
    end_time = time.time()
    print(f"Imagen {image_path} coloreada en {end_time - start_time} segundos.")
    return True

def colorize_images(target_path, colorizator, args):
    images = [os.path.join(args.path, x) for x in os.listdir(args.path) if x.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
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
        # Mantén la estructura de las subcarpetas al definir save_path
        relative_path = os.path.relpath(image_path, temp_path)
        save_path = os.path.join(temp_path, relative_path)
        # Asegúrate de que la subcarpeta exista
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        save_path = convert_webp_to_png(save_path, temp_path)
        convert_to_bw(save_path)
        res_flag = colorize_single_image(image_path, save_path, colorizator, args)
        
        result_images.append(save_path if res_flag else image_path)
        
    result_name = os.path.join(os.path.dirname(file_path), 'colorization', file_name + '_colorized.cbz')
    
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
        # Procesar archivos .cbr en la carpeta
        cbr_files = [x.as_posix() for x in Path(args.path).rglob("*.cbr")]
        for cbr_file in cbr_files:
            colorize_cbr(cbr_file, colorizer, args)
    elif os.path.isfile(args.path):
        split = os.path.splitext(args.path)
        if split[1].lower() in ('.jpg', '.png', '.jpeg', '.webp'):
            new_image_path = split[0] + '_colorized' + '.png'
            colorize_single_image(args.path, new_image_path, colorizer, args)
        elif split[1].lower() in ('.cbr'):
            colorize_cbr(args.path, colorizer, args)
