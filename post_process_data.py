import argparse
import csv
import glob
import json
import os
import traceback
from datetime import datetime
from os.path import join

import pandas as pd
from pydub import AudioSegment

import global_constants as constant
import function_library


# Reads files with the specified Noise types in allowed values'
def read_files(file_list, columns):
    result_dataframe = pd.DataFrame()
    if len(file_list) == 0:
        return result_dataframe

    for file_name in file_list:
        data_frame = pd.read_csv(file_name, names=columns, usecols=range(len(columns)))
        if len(data_frame) == 0:
            continue

        result_dataframe = result_dataframe.append(data_frame, ignore_index=True)

    result_dataframe = result_dataframe[result_dataframe["noise"] != -1]
    return result_dataframe


# Copies the files stored in the log file from the specified source location to "Test_Data/vX" folder, X is version no.
def compile_audio_gt_files(file_dataframe, source, data_version, captcha_type, Test_Data):

    version_folder = join(constant.DATA_FOLDER, Test_Data, "v" + data_version,
                          "time_" + str(datetime.now().timestamp()).replace(".", "") + "_c_" + constant.CAPTCHA_TYPE)
    audio_destination = join(version_folder, "audio")
    os.makedirs(audio_destination, exist_ok=True)

    dictionary_gt, audio_name_list = [], []
    rows = [["Name", "Captcha"]]

    for index, row in file_dataframe.iterrows():
        audio_file = row["name"]

        if captcha_type == "4":
            transcript = row["reduced_word"]
        else:
            if row["first_word_easy"]:
                transcript = row["first_word"]
            else:
                transcript = row["second_word"]

        dictionary_gt.append({"audio": audio_file + ".wav", "gt": transcript})
        audio_name_list.append({"audio": audio_file + ".wav"})
        rows.append([audio_file, captcha_type])

        audio = AudioSegment.from_file(join(source, audio_file + ".wav"), format="wav")
        output_path = os.path.join(audio_destination, audio_file + ".wav")
        audio.export(output_path, format="wav")

    gt_folder = join(version_folder, "gt_data")
    os.makedirs(gt_folder, exist_ok=True)
    json.dump(dictionary_gt, open(os.path.join(gt_folder, "gt" + captcha_type + ".json"), "w"))

    audio_folder = join(version_folder, "audioname")
    os.makedirs(audio_folder, exist_ok=True)
    json.dump(audio_name_list, open(os.path.join(audio_folder, "aname" + captcha_type + ".json"), "w"))

    selection_folder = join(version_folder, "selection")
    os.makedirs(selection_folder, exist_ok=True)
    with open(os.path.join(selection_folder, "sample" + captcha_type + ".csv"), "w", newline="") as sample_file:
        csv.writer(sample_file).writerows(rows)

    return audio_name_list


# Argument Parsing code
arg_object = argparse.ArgumentParser()

arg_object.add_argument("-g", "--group", help="data in example sub folder path/name/tag", default="youtube_lecture")
arg_object.add_argument("-d", "--data", help="data folder path. Other folders are relative to this folder", default="reboot_rerun")
arg_object.add_argument("-i", "--input", help="input sub folder", default="input")
arg_object.add_argument("-s", "--selected", help="Clips sent to IBM and selected for CAPTCHA", default='selected')
arg_object.add_argument("-t", "--captcha_type", help="The CAPTCHA type to be generated", default="3b")

arg_object.add_argument("-l", "--logs_path", help="usual_log_path", default="logs")
arg_object.add_argument("-v", "--data_version", default="Reboot5", help="data_version is used to tag different versions of data. For example, Indian, American and reboot")
arg_object.add_argument("-f", "--test_data", default='Test_Data', help="final Test_Data folder")

args = arg_object.parse_args()

constant.DATA_FOLDER = args.data
constant.INPUT_DATA_STAGE = join(constant.DATA_FOLDER, args.input)
constant.OUTPUT_DATA_SELECTED = join(constant.DATA_FOLDER, args.selected)
constant.CAPTCHA_TYPE = args.captcha_type

print("Global contants set to : ")
print("Group", args.group)
print("DATA_FOLDER", constant.DATA_FOLDER)
print("INPUT_DATA", constant.INPUT_DATA_STAGE)
print("OUTPUT_DATA_SELECTED", constant.OUTPUT_DATA_SELECTED)
print("CAPTCHA_TYPE", constant.CAPTCHA_TYPE)

# This tag is used to filter the total number of files in the csv files for the post-processing step.
# The files in these filtered subset are compiled and moved to a common location, to be consumed by the Javascript code.
output_file_tag = function_library.get_tag(constant.CAPTCHA_TYPE)

try:
    complete_file_list = glob.glob(join(args.logs_path, "*" + "selected" + "*" + output_file_tag + ".csv"))

    if constant.CAPTCHA_TYPE == "4":
        column_word = ["name", "version", "original_text", "noise", "complete", "source_type", "noise_type",
                       "transcript", "reduced_word"]
    else:
        column_word = ["name", "version", "start", "end", "original_text", "noise", "first_word_easy",
                       "first_confidence", "second_confidence", "source_type", "noise_type", "first_word",
                       "second_word"]

    file_dataframe = read_files(complete_file_list, column_word)
    audio_list = compile_audio_gt_files(file_dataframe, constant.OUTPUT_DATA_SELECTED, args.data_version, constant.CAPTCHA_TYPE, args.test_data)
    print("Number of audio files compiled - " + str(len(audio_list)))

except Exception as uE:
    print("Unknown error. " + str(uE))
    traceback.print_exc()

print("Done, exiting.")