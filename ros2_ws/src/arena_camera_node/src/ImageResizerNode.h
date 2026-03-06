#pragma once

#include <string>

#include <image_transport/image_transport.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>

class ImageResizerNode : public rclcpp::Node
{
 public:
  explicit ImageResizerNode(
      const rclcpp::NodeOptions& options = rclcpp::NodeOptions());

 private:
  void parse_parameters_();
  void initialize_io_();
  void image_callback_(const sensor_msgs::msg::Image::ConstSharedPtr& image_msg);

  int interpolation_from_string_(const std::string& interpolation_name) const;
  int cv_type_from_encoding_(const std::string& encoding) const;

  std::string input_topic_;
  std::string output_topic_;
  std::string qos_reliability_;
  std::string interpolation_name_;

  int output_width_;
  int output_height_;
  int interpolation_;

  image_transport::Subscriber input_sub_;
  image_transport::Publisher output_pub_;
};
