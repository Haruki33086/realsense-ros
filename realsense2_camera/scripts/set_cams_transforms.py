import sys
import rclpy
import geometry_msgs.msg as geometry_msgs
import tf2_ros
# from tf2_py import transformations as tf_trans

import termios
import tty
import os
import time
import math
import json
from rclpy.clock import Clock
from tf_transformations import euler_from_quaternion, quaternion_from_euler



def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def main():
    return


def print_status(status):
    sys.stdout.write('%-8s%-8s%-8s%-40s\r' % (status['mode'], status[status['mode']]['value'], status[status['mode']]['step'], status['message']))


def publish_status(broadcaster, status):
    time_stamp = Clock().now()
    static_transform_stamped = geometry_msgs.TransformStamped()
    static_transform_stamped.header.stamp = time_stamp.to_msg()
    static_transform_stamped.header.frame_id = status['from_cam']

    static_transform_stamped.child_frame_id = status['to_cam']
    static_transform_stamped.transform.translation.x = status['x']['value']
    static_transform_stamped.transform.translation.y = status['y']['value']
    static_transform_stamped.transform.translation.z = status['z']['value']

    quat = quaternion_from_euler(math.radians(status['roll']['value']),
                                          math.radians(status['pitch']['value']),
                                          math.radians(status['azimuth']['value']))
    static_transform_stamped.transform.rotation.x = quat[0]
    static_transform_stamped.transform.rotation.y = quat[1]
    static_transform_stamped.transform.rotation.z = quat[2]
    static_transform_stamped.transform.rotation.w = quat[3]
    broadcaster.sendTransform(static_transform_stamped)


if __name__ == '__main__':
    rclpy.init(args=sys.argv)
    
    if len(sys.argv) < 3:
        print('USAGE:')
        print('set_cams_transforms.py from_cam to_cam x y z azimuth pitch roll')
        print('x, y, z: in meters')
        print('azimuth, pitch, roll: in degrees')
        print()
        print('If parameters are not given read last used parameters.')
        print()
        print('[OPTIONS]')
        print('--file <file name> : if given, default values are loaded from file')
        sys.exit(-1)

    from_cam, to_cam = sys.argv[1:3]
    try:
        filename = sys.argv[sys.argv.index('--file')+1]
        print('Using file %s' % os.path.abspath(filename))
    except:
        filename = os.path.join(os.path.dirname(__file__), '_set_cams_info_file.txt')
        print('Using default file %s' % os.path.abspath(filename))

    if len(sys.argv) >= 9:
        x, y, z, yaw, pitch, roll = [float(arg) for arg in sys.argv[3:10]]
        status = {'mode': 'pitch',
                  'x': {'value': x, 'step': 0.1},
                  'y': {'value': y, 'step': 0.1},
                  'z': {'value': z, 'step': 0.1},
                  'azimuth': {'value': yaw, 'step': 1},
                  'pitch': {'value': pitch, 'step': 1},
                  'roll': {'value': roll, 'step': 1},
                  'message': '',
                  'from_cam': from_cam,
                  'to_cam': to_cam}
        print('Use given initial values.')
    else:
        try:
            status = json.load(open(filename, 'r'))
            print('Read initial values from file.')
        except IOError as e:
            print('Failed reading initial parameters from file %s' % filename)
            print('Initial parameters must be given for initial run or if an un-initialized file has been given.')
            sys.exit(-1)

    node = rclpy.create_node('my_static_tf2_broadcaster')
    broadcaster = tf2_ros.StaticTransformBroadcaster(node)

    print()
    print('Press the following keys to change mode: x, y, z, (a)zimuth, (p)itch, (r)oll')
    print('For each mode, press 6 to increase by step and 4 to decrease')
    print('Press + to multiply step by 2 or - to divide')
    print()
    print('Press Q to quit')
    print()

    status_keys = [key for key in status.keys()]
    print('%-8s%-8s%-8s%s' % ('Mode', 'value', 'step', 'message'))
    print_status(status)
    publish_status(broadcaster, status)
    while True:
        kk = getch()
        status['message'] = ''
        try:
            key_idx = status_keys.index(kk)
            status['mode'] = status_keys[key_idx]
        except ValueError as e:
            if kk.upper() == 'Q':
                sys.stdout.write('\n')
                break
            elif kk == '4':
                status[status['mode']]['value'] -= status[status['mode']]['step']
            elif kk == '6':
                status[status['mode']]['value'] += status[status['mode']]['step']
            elif kk == '-':
                status[status['mode']]['step'] /= 2.0
            elif kk == '+':
                status[status['mode']]['step'] *= 2.0
            else:
                status['message'] = 'Invalid key:' + kk

        print_status(status)
        publish_status(broadcaster, status)
        json.dump(status, open(filename, 'w'), indent=4)

    node.destroy_node()
    rclpy.shutdown()
