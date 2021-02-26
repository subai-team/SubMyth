import subprocess
from PyQt5.QtGui import QImage, QColor
import xml.etree.ElementTree as ET


def load_colors():
    tree = ET.parse('res/colors.xml')
    root = tree.getroot()
    colors = {}
    for child in root:
        color = QColor(child.text)
        colors[child.attrib["name"]] = color
    return colors


def load_icons():
    tree = ET.parse('res/icons.xml')
    root = tree.getroot()
    icons = {}
    for child in root:
        image = QImage('icons/{0}'.format(child.text))
        if "width" in child.attrib.keys():
            width = int(child.attrib["width"])
            image = image.scaledToWidth(width)
        if "height" in child.attrib.keys():
            height = int(child.attrib["height"])
            image = image.scaledToHeight(height)
        icons[child.attrib["name"]] = image
    return icons


def load_strings(lang):
    tree = ET.parse('res/strings.xml')
    root = tree.getroot()
    for child in root:
        if child.attrib["lang"] == lang:
            root = child
            break
    strings = {}
    for child in root:
        strings[child.attrib["name"]] = child.text
    return strings


def get_file_format(file_name):
    if file_name[-4:] == ".srt":
        return "srt"
    elif file_name[-5:] == ".smpr":
        return "smpr"
    elif  file_name[-4:] == ".wav":
        return "wav"


def add_file_format(file_name, file_format):
    length = len(file_format) + 1
    if file_name[-length:] == "." + file_format:
        return file_name
    else:
        return file_name + "." + file_format


def convert_to_wav(input):
    command = "ffmpeg -i {0} -ar 22500 -ac 1 /tmp/test.wav"
    subprocess.run(command)
