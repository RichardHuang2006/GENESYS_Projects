import rospy
from geometry_msgs.msg import Twist
import math
import os
import time
from nav_msgs.msg import Odometry
import tf
import math

def get_yaw_once(log = False):
    rospy.init_node('turtlebot_turn_90', anonymous=True)
    msg = rospy.wait_for_message("/odom", Odometry)

    orientation_q = msg.pose.pose.orientation
    quaternion = (
        orientation_q.x,
        orientation_q.y,
        orientation_q.z,
        orientation_q.w
    )
    (roll, pitch, yaw) = tf.transformations.euler_from_quaternion(quaternion)
    yaw_degrees = math.degrees(yaw)

    if(log):
        rospy.loginfo("Bearing (Yaw): {:.2f} degrees".format(yaw_degrees))
    return yaw

def move_backwards():
    rospy.init_node('turtlebot_backwards', anonymous=True)
    pub = rospy.Publisher('/mobile_base/commands/velocity', Twist, queue_size=10)
    rate = rospy.Rate(10)  # 10 Hz

    move_cmd = Twist()
    move_cmd.linear.x = -0.1  # Move backwards
    move_cmd.angular.z = 0.0  # No rotation

    # Publish for a short time (e.g., 2 seconds)
    timeout = rospy.Time.now() + rospy.Duration(2.0)
    while rospy.Time.now() < timeout and not rospy.is_shutdown():
        pub.publish(move_cmd)
        rate.sleep()

    # Stop the robot
    stop_cmd = Twist()
    pub.publish(stop_cmd)


def publish_once():
    rospy.init_node('turtlebot_publish_once', anonymous=True)
    pub = rospy.Publisher('/mobile_base/commands/velocity', Twist, queue_size=10)

    # Wait for the publisher to establish connection
    rospy.sleep(1.0)

    move_cmd = Twist()
    move_cmd.linear.x = -0.1  # Move backward
    move_cmd.angular.z = 0.0

    pub.publish(move_cmd)
    rospy.loginfo("Published one velocity command.")

def move(move_val):
    rospy.init_node('turtlebot_turn_90', anonymous=True)
    pub = rospy.Publisher('/mobile_base/commands/velocity', Twist, queue_size=10)

    # Wait for the publisher to establish connection
    rospy.sleep(1.0)

    move_cmd = Twist()
    move_cmd.linear.x = move_val  # Move backward
    move_cmd.angular.z = 0.0

    pub.publish(move_cmd)
    rospy.loginfo("Published one velocity command.")

def turn_90_degrees(clockwise=False):
    rospy.init_node('turtlebot_turn_90', anonymous=True)
    pub = rospy.Publisher('/mobile_base/commands/velocity', Twist, queue_size=10)
    rospy.sleep(1.0)

    yaw = get_yaw_once(log = True)

    # Desired angle and angular speed
    angular_speed = 0.25  # radians/sec (safe value for TurtleBot2)

    if clockwise:
        desired_yaw = yaw - math.pi/2
    else:
        desired_yaw = yaw + math.pi/2

    if clockwise:
        angular_speed = -abs(angular_speed)
    else:
        angular_speed = abs(angular_speed)

    move_cmd = Twist()
    move_cmd.angular.z = angular_speed

    rate = rospy.Rate(10)  # 10 Hz

    if clockwise:
        while yaw > desired_yaw:
            yaw = get_yaw_once()
            pub.publish(move_cmd)
            rate.sleep()
    else:
        while yaw < desired_yaw:
            yaw = get_yaw_once()
            pub.publish(move_cmd)
            rate.sleep()

    

    # Stop
    stop_cmd = Twist()
    pub.publish(stop_cmd)

    rospy.loginfo("Completed 90-degree turn")
    yaw = get_yaw_once(log = True)

def correct_yaw(desired_yaw):
    rospy.init_node('turtlebot_turn_90', anonymous=True)
    pub = rospy.Publisher('/mobile_base/commands/velocity', Twist, queue_size=10)
    rospy.sleep(1.0)
    #print("Desired yaw: ", desired_yaw)
    yaw = get_yaw_once(log = False)

    # Desired angle and angular speed
    angular_speed = 0.15  # radians/sec (safe value for TurtleBot2)

    move_cmd = Twist()
    move_cmd.angular.z = angular_speed

    rate = rospy.Rate(10)  # 10 Hz

    #print("Yaw diff: ", abs(desired_yaw - yaw))

    while abs(desired_yaw - yaw) > 0.07:
        if desired_yaw - yaw < 0:
            angular_speed = -0.25
            move_cmd.angular.z = angular_speed
            yaw = get_yaw_once(log = False)
            pub.publish(move_cmd)
            rate.sleep()
        else:
            angular_speed = 0.25
            move_cmd.angular.z = angular_speed
            yaw = get_yaw_once(log = False)
            pub.publish(move_cmd)
            rate.sleep()
    

    # Stop
    stop_cmd = Twist()
    pub.publish(stop_cmd)

    #rospy.loginfo("Corrected Yaw")
    yaw = get_yaw_once(log = False)

def move_next_row():
    turn_90_degrees(clockwise=False)
    time.sleep(0.1)
    move(-0.5)
    time.sleep(0.1)
    turn_90_degrees(clockwise=True)

#move(-0.2)

#move_next_row()
#get_yaw_once()
#time.sleep(0.1)
#turn_90_degrees()
#time.sleep(0.1)
#get_yaw_once()