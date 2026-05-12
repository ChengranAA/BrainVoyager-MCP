import numpy as np
import nibabel as nib
import bvbabel as bvb
import os
import pydicom
import json
from glob import glob

def get_n_slices(dicom_folder, dicom_filename):
        # get number of slices
        prefix = dicom_filename.split('00001')[0]
        n_slices = len(glob(f'{dicom_folder}/{prefix}*'))
        return n_slices

def create_vmr_dict(dicom_folder, subj_id, save=False):
        prefix = glob(dicom_folder + '/*')[0].split('/')[-1].split('-')[-4]
        suffix = '-0001-00001.dcm'
        v1i1 = [f for f in os.listdir(dicom_folder) if prefix in f and suffix in f]
        project_dict = {}
        for filename in v1i1:
            ds = pydicom.dcmread(f'{dicom_folder}/{filename}')

            if 'INV' in ds.SeriesDescription and \
               'PHS' not in ds.SeriesDescription:
                contrast_img = ds.SeriesDescription.split('_')[-1]
            elif 'T1_Images' in ds.SeriesDescription:
                contrast_img = 'T1'
            elif 'UNI_Images' in ds.SeriesDescription:
                contrast_img = 'UNI'
            else:
                contrast_img = None
            if contrast_img:
                n_slices = get_n_slices(dicom_folder, filename)
                project_dict[filename] = {'contrast_img': contrast_img,
                                          'subject_id': subj_id,
                                          'filename': filename,
                                          'n_slices' : n_slices}
        if save:
            with open(f'{save}/vmr_info.json', 'w') as outfile:
                json.dump(project_dict, outfile)

        return project_dict

def mp2rage_robustfunc(INV1, INV2, beta):
    """adaptation of matlab robust denoise function"""
    return (np.conj(INV1)*INV2-beta)/(INV1**2+INV2**2+2*beta)

def rootsquares_pos(a, b, c):
    # matlab:rootsquares_pos=@(a, b, c)(-b+sqrt(b. ^ 2 - 4 * a.*c))./(2*a)
    return (-b+np.sqrt(b**2 - 4*a*c))/(2*a)

def rootsquares_neg(a, b, c):
    # matlab: rootsquares_neg = @(a, b, c)(-b-sqrt(b. ^ 2 - 4 * a.*c))./(2*a)
    return (-b-np.sqrt(b**2 - 4*a*c))/(2*a)

def mp2rage_genUniDen(chosen_factor, path_UNI, path_INV1, path_INV2, uniden_filename="uniden.v16", savevmr=True):
    """function to take mp2rage files uni, inv1 and inv2 and given a chosen factor
    returns denoised images. Saves the output in the same directory as path_UNI
    and returns only the saved path."""

    print(path_UNI)

    # load data
    header, mp2rage_img = bvb.v16.read_v16(path_UNI)
    _, inv1_img = bvb.v16.read_v16(path_INV1)
    _, inv2_img = bvb.v16.read_v16(path_INV2)

    print(mp2rage_img.shape)
    print(header)

    # adjust dimensions for slight mismatches of phase data
    if inv1_img.shape != mp2rage_img.shape:
        tp_img = np.zeros(mp2rage_img.shape)
        tp_img[:inv1_img.shape[0], :inv1_img.shape[1], :inv1_img.shape[2]] = inv1_img
        inv1_img = tp_img
    if inv2_img.shape != mp2rage_img.shape:
        tp_img = np.zeros(mp2rage_img.shape)
        tp_img[:inv2_img.shape[0], :inv2_img.shape[1], :inv2_img.shape[2]] = inv2_img
        inv2_img = tp_img

    mp2rage_img = mp2rage_img.astype('float64')
    inv1_img = inv1_img.astype('float64')
    inv2_img = inv2_img.astype('float64')

    if mp2rage_img.min() >= 0 and mp2rage_img.max() >= 0.51:
        # converts MP2RAGE to -0.5 to 0.5 scale - assumes that it is getting only positive values
        mp2rage_img = (
            mp2rage_img - mp2rage_img.max()/2)/mp2rage_img.max()

    # computes correct INV1 dataset
    inv1_img = np.sign(mp2rage_img)*inv1_img # gives the correct polarity to INV1

    # because the MP2RAGE INV1 and INV2 is a sum of squares data, while the
    # MP2RAGEimg is a phase sensitive coil combination.. some more maths has to
    # be performed to get a better INV1 estimate which here is done by assuming
    # both INV2 is closer to a real phase sensitive combination
    inv1pos = rootsquares_pos(-mp2rage_img, inv2_img, -inv2_img**2*mp2rage_img)
    inv1neg = rootsquares_neg(-mp2rage_img, inv2_img, -inv2_img**2*mp2rage_img)

    inv1final = inv1_img

    inv1final[np.absolute(inv1_img-inv1pos) > np.absolute(inv1_img-inv1neg)
              ] = inv1neg[np.absolute(inv1_img-inv1pos) > np.absolute(inv1_img-inv1neg)]
    inv1final[np.absolute(inv1_img-inv1pos) <= np.absolute(inv1_img-inv1neg)
              ] = inv1pos[np.absolute(inv1_img-inv1pos) <= np.absolute(inv1_img-inv1neg)]

    # usually the multiplicative factor shouldn't be greater then 10, but that
    # is not the case when the image is bias field corrected, in which case the
    # noise estimated at the edge of the imagemight not be such a good measure

    multiplyingFactor = chosen_factor
    noiselevel = multiplyingFactor*np.mean(inv2_img[:, -11:, -11:])

    # run the actual denoising function
    mp2rage_imgRobustPhaseSensitive = mp2rage_robustfunc(inv1final, inv2_img, noiselevel**2)

    # set to interger format
    mp2rageimg_img = np.round(4095*(mp2rage_imgRobustPhaseSensitive+0.5))

    #########
    # save image
    #########

    mp2rageimg_img = nib.casting.float_to_int(mp2rageimg_img,'int16')

    # Construct the output path in the same directory as path_UNI
    uni_directory = os.path.dirname(path_UNI)
    path_uniden_output = os.path.join(uni_directory, uniden_filename)

    # Always save v16
    bvb.v16.write_v16(path_uniden_output, header, mp2rageimg_img)

    if savevmr:
        mp2rageimg_img = np.uint8(np.round(225*(mp2rage_imgRobustPhaseSensitive+0.5)))

        # safely extract the base path without extension to append .vmr
        vmr_in_path = f"{os.path.splitext(path_UNI)[0]}.vmr"
        vmr_out_path = f"{os.path.splitext(path_uniden_output)[0]}.vmr"

        vmrheader, _ = bvb.vmr.read_vmr(vmr_in_path)
        bvb.vmr.write_vmr(vmr_out_path, vmrheader, mp2rageimg_img)

    return path_uniden_output
