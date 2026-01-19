import argparse
import os
from typing import Tuple
import xml.etree.ElementTree as ET
from skimage.color import rgb2lab, deltaE_ciede2000
import json
import numpy as np
from numpy.typing import NDArray

def execute():
    parser = argparse.ArgumentParser(
      description = "Take in an SVG and separate it into SVGs group by colors"
    )

    parser.add_argument('input', type=str)
    parser.add_argument('-o', '--output', required=False, type=str)
    parser.add_argument('-m' '--mapping', required=True, type=str)
    args = parser.parse_args()

    input_path: str = args.input
    validate_input_path(input_path)

    output_path: str = sanitize_output_path(input_path, args.output)

    mapping_path: str = args.m__mapping
    validate_mapping_path(mapping_path)

    separate_svg(input_path, output_path, mapping_path)

def validate_input_path(input: str):
    if not os.path.exists(input):
        raise Exception(f'Input path "{input}" is not a valid path.')
    
    if not os.path.splitext(input)[1].lower() == ".svg":
        raise Exception(f'Input file is not a svg file')
  
def sanitize_output_path(input: str, output: str):
    output_path = output
    if output_path == None:
        input_dir = os.path.split(input)[0]
        output_path = os.path.join(input_dir, 'svg-output')

    if not os.path.exists(output_path):
        os.mkdir(output_path)

    return output_path

def validate_mapping_path(mapping_path: str):
    if not os.path.exists(mapping_path):
        raise Exception(f'Mapping path "{mapping_path}" is not a valid path.')

def separate_svg(input: str, output: str, mapping_path: str):
    mapping_data = load_mapping_data(mapping_path)
    colors_splitted = split_color_from_xml(input)

    final_colors = combine_similar_color(colors_splitted, mapping_data)

    tree = ET.parse(input)
    root_attrib = tree.getroot().attrib
    root_attrib['xmlns'] = 'http://www.w3.org/2000/svg'
    for color in final_colors:
        if len(final_colors[color]) > 0:
            create_svg(mapping_data[color], final_colors[color], root_attrib, output)

def load_mapping_data(mapping_path: str):
    try:
        with open(mapping_path, 'r') as file:
          return json.load(file)
    except json.JSONDecodeError:
        raise(f'Error loading data from {mapping_path}')

def create_svg(color_name: str, paths: list, root_attr: dict[str, str], output: str):
    root = ET.Element("svg", root_attr)
    for path in paths:
        ET.SubElement(root, "path", path.attrib)

    xml_declaration = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
    svg_doctype = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
    xmlstr = ET.tostring(root, encoding='unicode')
    xmlstr = f'{xml_declaration}\n{svg_doctype}\n{xmlstr}'
    with open(os.path.join(output, f'{color_name}.svg'), 'w') as f:
        f.write(xmlstr)

def split_color_from_xml(input: str):
    tree = ET.parse(input)
    root = tree.getroot()
    
    paths = root.findall('{http://www.w3.org/2000/svg}path')
    color_paths = {}

    for path in paths:
      color = path.attrib['fill']
      if not color in color_paths:
        color_paths[color] = list()
      
      color_paths[color].append(path)
      
    return color_paths

  # paths = {}
  # for path in defs:
  #     paths[path.attrib['id']] = path.attrib

  # gs = root.findall('{http://www.w3.org/2000/svg}g')
  # g = next(x for x in gs if len(x.attrib) == 0)
  
  # color_paths = {}
  # for fill in g:
  #     color = fill.attrib['fill']
  #     if not color in color_paths:
  #         color_paths[color] = list()
      
  #     path_id = fill.attrib['{http://www.w3.org/1999/xlink}href']
  #     path_attrib = paths[path_id[1:]]
  #     path_attrib['fill'] = color

  #     color_paths[color].append(path_attrib)
  
  # return color_paths

def combine_similar_color(colors_splitted, mapping_data):
    output_map = {}
    for key in mapping_data:
        output_map[key] = list()

    rgb_lab_map = {}
    for rgb in mapping_data:
        rgb_lab_map[rgb] = convert_rgb_to_lab(parse_color(rgb))
    
    for color in colors_splitted:
        closest_color = find_closest_color(color, rgb_lab_map)
        output_map[closest_color].extend(colors_splitted[color])
    
    return output_map
    
def convert_rgb_to_lab(rgb: Tuple[int, int, int]) -> NDArray[np.floating]:
    rgb_normalized: NDArray[np.floating] = np.array(rgb) / 255.0
    rgb_image: NDArray[np.floating] = rgb_normalized.reshape(1, 1, 3)
    lab_image:NDArray[np.floating] = rgb2lab(rgb_image)

    return lab_image[0, 0]

def parse_color(color_str: str):
    color = color_str[1:]
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

def find_closest_color(color, rgb_lab_map) -> str:
    best_distance: float = float('inf')
    closest_color: str = None

    lab_to_compare: NDArray[np.floating] = convert_rgb_to_lab(parse_color(color))
    for rgb in rgb_lab_map:
        map_lab = rgb_lab_map[rgb]
        dist: float = deltaE_ciede2000(
            np.array([lab_to_compare]),
            np.array([map_lab])
        )[0]

        if dist < best_distance:
            best_distance = dist
            closest_color = rgb
    
    return closest_color

if __name__ == "__main__":
    execute()