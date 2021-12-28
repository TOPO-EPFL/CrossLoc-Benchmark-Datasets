import argparse
import os.path
import pdb
import random
from setup_dataset_utils import *


def get_ecef_origin():
    """Shift the origin to make the value of coordinates in ECEF smaller and increase training stability"""
    # Warning: this is dataset specific!
    ori_lon, ori_lat, ori_alt = 6.5668, 46.5191, 390
    ori_x, ori_y, ori_z = pyproj.Transformer.from_crs("epsg:4979", "epsg:4978").transform(ori_lat, ori_lon, ori_alt)
    print('Origin XYZ: {}, {}, {}'.format(ori_x, ori_y, ori_z))
    origin = np.array([ori_x, ori_y, ori_z], dtype=np.float64)
    return origin


def main(args):
    """Setup the dataset"""

    print('===== Urbanscape dataset setup starts =====')

    origin = get_ecef_origin()

    args.lhs_dir = os.path.abspath(os.path.join(args.dataset_dir, args.lhs_dir))
    args.matching_dir = os.path.abspath(os.path.join(args.dataset_dir, args.matching_dir))

    # Check raw data folder paths
    assert os.path.exists(args.lhs_dir)
    assert os.path.exists(args.matching_dir)

    dst_dir = os.path.abspath(args.output_dir)
    mkdir(dst_dir)

    # Get matching data directories
    drone_data_cesium_ls, drone_data_real_ls = [], []
    oop_drone_data_cesium_ls, oop_drone_data_real_ls = [], []  # out of place data
    for root, dirs, files in os.walk(args.matching_dir):
        if len(files):
            if os.path.basename(root).endswith('-sim'):
                root_real = os.path.join(os.path.dirname(root), os.path.basename(root).replace('-sim', '-real'))
                assert os.path.exists(root_real)
                if 'outofplace' in os.path.basename(root):
                    oop_drone_data_cesium_ls.append(root)
                    oop_drone_data_real_ls.append(root_real)
                else:
                    drone_data_cesium_ls.append(root)
                    drone_data_real_ls.append(root_real)
    sort_idx = np.argsort(drone_data_cesium_ls)
    drone_data_cesium_ls = np.take(drone_data_cesium_ls, sort_idx).tolist()
    drone_data_real_ls = np.take(drone_data_real_ls, sort_idx).tolist()

    # Setup dataset folder by folder
    # lhs synthetic data
    process_folder(args.lhs_dir, None, dst_dir, 'lhs_sim', origin, args.stride, args.ignore_3d_label,
                   args.force_semantics_downsampling)

    # drone real-synthetic matching data
    for cesium_path, real_path in zip(drone_data_cesium_ls, drone_data_real_ls):
        process_folder(cesium_path, None, dst_dir, 'drone_sim', origin, args.stride, args.ignore_3d_label,
                       args.force_semantics_downsampling)
        process_folder(cesium_path, real_path, dst_dir, 'drone_real', origin, args.stride, args.ignore_3d_label,
                       args.force_semantics_downsampling)

    for cesium_path, real_path in zip(oop_drone_data_cesium_ls, oop_drone_data_real_ls):
        process_folder(cesium_path, None, dst_dir, 'oop_drone_sim', origin, args.stride, args.ignore_3d_label,
                       args.force_semantics_downsampling)
        process_folder(cesium_path, real_path, dst_dir, 'oop_drone_real', origin, args.stride, args.ignore_3d_label,
                       args.force_semantics_downsampling)

    # Split data into training/validation/testing
    for mode in ['lhs_sim', 'drone_sim', 'drone_real', 'oop_drone_sim', 'oop_drone_real']:
        print('\n===== Splitting data in {:s} mode ====='.format(mode))
        split_data(os.path.join(dst_dir, mode), mode, 'urbanscape', args.ignore_3d_label)
        shutil.rmtree(os.path.join(dst_dir, mode))

    # Construct virtual dataset pointer for ALL synthetic training data
    src_dir_ls = [os.path.join(dst_dir, 'train_sim'), os.path.join(dst_dir, 'train_drone_sim')]
    virtual_merge_sections(src_dir_ls, os.path.join(dst_dir, 'train_sim_plus_drone_sim'), args.ignore_3d_label)

    src_dir_ls = [os.path.join(dst_dir, 'train_sim'), os.path.join(dst_dir, 'train_oop_drone_sim')]
    virtual_merge_sections(src_dir_ls, os.path.join(dst_dir, 'train_sim_plus_oop_drone_sim'), args.ignore_3d_label)

    print('===== Urbanscape dataset setup is done =====')


if __name__ == '__main__':

    mp.set_start_method('spawn')

    parser = argparse.ArgumentParser(
        description='Setup CrossLoc Benchmark Urbanscape dataset.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--dataset_dir', type=str, required=True,
                        help='Dataset storing the structured datasets.')

    parser.add_argument('--lhs_dir', type=str, default='urbanscape-LHS',
                        help='Source directory for synthetic LHS dataset.')

    parser.add_argument('--matching_dir', type=str,
                        default='matching/',
                        help='Source directory for real-synthetic matching dataset.')

    parser.add_argument('--output_dir', type=str,
                        default=os.path.abspath(os.path.join(os.path.dirname(__file__), 'urbanscape')),
                        help='Destination directory for the organized dataset. Use DSAC* convention.')

    parser.add_argument('--stride', type=int, default=8,
                        help='Downsampling rate. This does not apply to semantics!')

    parser.add_argument('--force_semantics_downsampling', default=False, action='store_true',
                        help='Forcefully downsample semantic map. Please use carefully!')

    parser.add_argument('--ignore_3d_label', action='store_true',
                        help="Save RGB and semantic maps only. Ignore all 3D related labels.")

    args = parser.parse_args()
    print(args)

    # fix random seed for reproducibility
    np.random.seed(2021)
    random.seed(2021)

    main(args)
