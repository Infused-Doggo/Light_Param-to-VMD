import os.path

import nuthouse01.nuthouse01_vmd_struct as vmd_struct
import nuthouse01.nuthouse01_vmd_parser as vmd_parser


def user_input(string: str, is_int=False, is_file=False, is_folder=False):
    while True:
        result = input(string)

        if is_int:
            try:
                result = int(result)
                return result
            except Exception as e:
                print(e, "Not an int")

        elif is_file:
            result = result.strip('"')

            if os.path.isfile(result):
                return result

            else:
                print("Not a file")

        elif is_folder:
            result = result.strip('"')

            if os.path.isdir(result):
                return result

            else:
                print("Not a folder")


def parse_dsc_line(line: str):
    name, args = line[:len(line) - 2].split("(")
    args = args.split(", ")

    for idx, arg in enumerate(args):
        try:
            args[idx] = int(arg)
        except ValueError:
            try:
                args[idx] = float(arg)
            except ValueError:
                pass

    return name, args


def parse_pv_line(line: str):
    args = line.strip(" ").split(" ")

    for idx, arg in enumerate(args):
        try:
            args[idx] = int(arg)
        except ValueError:
            try:
                args[idx] = float(arg)
            except ValueError:
                pass

    return args


def parse_glow(file_path: str):
    with open(file_path, "r", encoding="UTF-8") as file:
        file = file.read().split("\n")

        values = {}

        for line in file:
            if not line:
                continue

            line = parse_pv_line(line)

            match line[0]:
                case "EOF":
                    break

                case "tone_map_method":
                    values["Tonemap_Type"] = {0: 0.333, 1: 0.666, 2: 0.999}[line[1]]

                case "fade_color":
                    values["Fade_R +"] = line[1]
                    values["Fade_G +"] = line[2]
                    values["Fade_B +"] = line[3]

                case "tone_transform":
                    values["R_Offset +"] = line[1]
                    values["G_Offset +"] = line[2]
                    values["B_Offset +"] = line[3]
                    values["R_Scale +"] = line[4]
                    values["G_Scale +"] = line[5]
                    values["B_Scale +"] = line[6]

                case "flare":
                    # values["Flare_X +"] = line[1]
                    # values["Flare_Y +"] = line[2]
                    # values["Flare_Z +"] = line[3]
                    pass

                case "sigma":
                    # values["Sigma_X +"] = line[1]
                    # values["Sigma_Y +"] = line[2]
                    # values["Sigma_Z +"] = line[3]
                    pass

                case "intensity":
                    # values["Intens_X +"] = line[1]
                    # values["Intens_Y +"] = line[2]
                    # values["Intens_Z +"] = line[3]
                    pass

                case _:
                    everything = {
                        "exposure": "Exposure +",
                        "gamma": "Gamma +",
                        "saturate_power": "Saturation_Pow",
                        "saturate_coef": "Saturation +",
                        "auto_exposure": "Auto_Exposure"
                    }

                    if line[0] in everything:
                        values[everything[line[0]]] = line[1]

    return values


def parse_light(file_path: str):
    with open(file_path, "r", encoding="UTF-8") as file:
        file = file.read().split("\n")

        values_bone = {}
        current_light_type = ""

        for line in file:
            if not line:
                continue

            line = parse_pv_line(line)

            match line[0]:
                case "EOF":
                    break

                case "id_start":
                    match line[1]:
                        case 0:
                            current_light_type = "Chara"

                        case 1:
                            current_light_type = "Stage"

                        case _:
                            current_light_type = ""

                case _:
                    everything = {
                        "ambient": "Ambient",
                        "diffuse": "Diffuse",
                        "specular": "Specular",
                        "position": "Direction"
                    }

                    if line[0] in everything and current_light_type:
                        if everything[line[0]]:
                            values_bone[f"{current_light_type}_{everything[line[0]]}"] = [
                                line[1:4], [line[4], 0, 0]
                            ]

    return values_bone


def sharp_interpolation(times, length, offset):
    new_list = []

    for i in range(1, length):
        for idx in range(1, len(times)):
            a, b = times[idx - 1], times[idx]

            if a == i and b == i:
                continue

            elif a <= i <= b:
                new_list.append([i - offset, idx - 1])
                break

    # new_list.append([new_list[-1][0] + 1, len(times) - 1])

    remove = []
    for idx in range(1, len(new_list) - 1):
        a, b, c = new_list[idx - 1], new_list[idx], new_list[idx + 1]

        if a[1] == b[1] and b[1] == c[1]:
            remove.append(idx)

    stuff = []
    for idx in range(len(new_list)):
        if idx not in remove:
            stuff.append(new_list[idx])

    return stuff


def parse_dsc(dsc_input: str, farc_content: str, frame_offset=1):
    while True:
        fps = user_input("Input your Framerate (30/60): ", is_int=True)

        if 0 < fps < 120:
            break

    with open(dsc_input, "r", encoding="UTF-8") as dsc_file:
        current_frame = 0
        morphs = {}
        bones = {}

        vmd = vmd_struct.Vmd(
            vmd_struct.VmdHeader(2, "Controller"), [], [], [], [], [], []
        )

        last_glow = []
        last_light_bone = []

        for line in dsc_file.read().split("\n"):
            if not line:
                continue

            name, args = parse_dsc_line(line)

            match name:
                case "TIME":
                    current_frame = int(args[0] / 100000 * fps) + frame_offset

                case "CHANGE_FIELD":
                    glow = None
                    light_bone = None

                    for file in os.listdir(farc_content):
                        file = file.lower()

                        if file.endswith(f"_c{args[0]:03}.txt"):
                            if file.startswith("glow_pv"):
                                glow = parse_glow(os.path.join(farc_content, file))
                                last_glow = glow

                            elif file.startswith("light_pv"):
                                light_bone = parse_light(os.path.join(farc_content, file))
                                last_light_bone = light_bone

                            else:
                                raise AssertionError(f"Idk what this file is {file}")

                    if not glow and last_glow:
                        glow = last_glow

                    if not light_bone and last_light_bone:
                        light_bone = last_light_bone

                    if current_frame not in morphs:
                        morphs[current_frame] = {}
                        bones[current_frame] = {}

                    morphs[current_frame].update(glow)
                    bones[current_frame].update(light_bone)

        get = [(x, y) for x, y in morphs.items()]

        for index, (key, value) in enumerate(sorted(morphs.items())):
            repeat = [key]

            if index != len(morphs) - 1:
                if key != get[index + 1][0] - 1:
                    repeat.append(get[index + 1][0] - 1)

            for i in repeat:
                for name, val in value.items():
                    vmd.morphframes.append(
                        vmd_struct.VmdMorphFrame(
                            f=i, name=name, val=val
                        )
                    )

        for index, (key, value) in enumerate(sorted(bones.items())):
            repeat = [key]

            if index != len(bones) - 1:
                if key != get[index + 1][0] - 1:
                    repeat.append(get[index + 1][0] - 1)

            for i in repeat:
                for name, (pos, rot) in value.items():
                    vmd.boneframes.append(
                        vmd_struct.VmdBoneFrame(
                            f=i, name=name, pos=pos, rot=rot, phys_off=False
                        )
                    )

        vmd_parser.write_vmd("PV_LIGHT.vmd", vmd)
    #Love ya Kimoo, mwa mwa mwa!!

if __name__ == "__main__":
    debug = False

    if debug:
        parse_dsc(
            dsc_input="DSC_Input.txt",
            farc_content="FARC_CONTENT",
            frame_offset=1
        )
    else:
        parse_dsc(
            dsc_input=user_input("Enter the parsed DSC file (.txt): ", is_file=True),
            farc_content=user_input("Drop the folder with the FARC lighting: ", is_folder=True),
            frame_offset=1
        )
    print("The output have been generated correctly.")