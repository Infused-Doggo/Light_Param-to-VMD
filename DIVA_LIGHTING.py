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


def parse_dsc(dsc_input: str, farc_content: str, mv_id=1, frame_offset=1):
    while True:
        fps = user_input("Input your Framerate (e.g. 30 or 60): ", is_int=True)

        if 0 < fps:
            break

    with open(dsc_input, "r", encoding="UTF-8") as dsc_file:
        current_frame = 0
        morphs, bones = {}, {}

        vmd = vmd_struct.Vmd(
            vmd_struct.VmdHeader(2, "Controller"), [], [], [], [], [], []
        )

        last_glow = []
        last_light_bone = []

        fallback_glow, fallback_light = [], []

        for line in dsc_file.read().split("\n"):
            if not line:
                continue

            name, args = parse_dsc_line(line)

            match name:
                case "TIME":
                    if args[0]:
                        current_frame = int(args[0] / 100000 * fps) + frame_offset

                    else:
                        current_frame = 0

                case "CHANGE_FIELD":
                    glow = None
                    light_bone = None

                    default_glow = []
                    default_light = []

                    for file in os.listdir(farc_content):
                        file = file.lower()

                        if file.endswith(f"pv{mv_id:03}_c{args[0]:03}.txt"):
                            if file.startswith("glow_pv"):
                                glow = parse_glow(os.path.join(farc_content, file))
                                last_glow = glow

                            elif file.startswith("light_pv"):
                                light_bone = parse_light(os.path.join(farc_content, file))
                                last_light_bone = light_bone

                        if not last_glow:
                            if file.startswith(f"glow_pv{mv_id:03}s") and file.endswith(".txt"):
                                default_glow.append(file)

                            if file == "glow_tst.txt":
                                fallback_glow = parse_glow(os.path.join(farc_content, file))

                        if not last_light_bone:
                            if file.startswith(f"light_pv{mv_id:03}s") and file.endswith(".txt"):
                                default_light.append(file)

                            if file == "light_tst.txt":
                                fallback_light = parse_light(os.path.join(farc_content, file))

                    # If nothing exists, pick default
                    if not glow and not last_glow:
                        if default_glow:
                            if len(default_glow) == 1:
                                last_glow = parse_glow(os.path.join(farc_content, default_glow[0]))

                            else:
                                print("I found multiple possible default glow files!")
                                print("Pick an index of a lighting that most likely appears first.")
                                print("It's likely that it will be the file with s01 in its name.")
                                print({x: y for x, y in enumerate(default_glow)})

                                while True:
                                    try:
                                        result = default_glow[
                                            user_input("Glow index: ", is_int=True)
                                        ]
                                        last_glow = parse_glow(os.path.join(farc_content, result))
                                        break

                                    except IndexError:
                                        print("Can't pick a file with given index.")

                        else:
                            raise FileNotFoundError

                    if not light_bone and not last_light_bone:
                        if default_light:
                            if len(default_light) == 1:
                                last_light_bone = parse_light(os.path.join(farc_content, default_light[0]))

                            else:
                                print("I found multiple possible default light files!")
                                print("Pick an index of a lighting that most likely appears first.")
                                print("It's likely that it will be the file with s01 in its name.")
                                print({x: y for x, y in enumerate(default_light)})

                                while True:
                                    try:
                                        result = default_light[
                                            user_input("Light index: ", is_int=True)
                                        ]
                                        last_light_bone = parse_light(os.path.join(farc_content, result))
                                        break

                                    except IndexError:
                                        print("Can't pick a file with given index.")

                        else:
                            raise FileNotFoundError

                    # If default doesn't exist, pick test
                    if not last_glow and fallback_glow:
                        last_glow = fallback_glow
                    else:
                        raise FileNotFoundError

                    if not last_light_bone and fallback_light:
                        last_light_bone = fallback_light
                    else:
                        raise FileNotFoundError

                    # No current file, replace with last
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

        vmd_parser.write_vmd(f"PV_LIGHT_{mv_id:03}.vmd", vmd)
    # Love ya Kimoo, mwa mwa mwa!!
    # Love ya too, mwa mwa mwa!!!


if __name__ == "__main__":
    debug = False

    if debug:
        parse_dsc(
            dsc_input="DSC_Input2.txt",
            farc_content="FARC_CONTENT",
            mv_id=19,
            frame_offset=1
        )
    else:
        parse_dsc(
            dsc_input=user_input("Enter the parsed DSC file (.txt): ", is_file=True),
            farc_content=user_input("Drop the folder with the FARC lighting: ", is_folder=True),
            mv_id=user_input("What's the song ID?: ", is_int=True),
            frame_offset=1
        )

    input("The output have been generated correctly. Press ENTER to exit... ")
