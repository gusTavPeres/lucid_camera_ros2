#include "ImageResizerNode.h"

#include <cstring>
#include <functional>
#include <stdexcept>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <sensor_msgs/image_encodings.hpp>

ImageResizerNode::ImageResizerNode(const rclcpp::NodeOptions& options)
    : Node("image_resizer_node", options)
{
  parse_parameters_();
  initialize_io_();
}

void ImageResizerNode::parse_parameters_()
{
  input_topic_ =
      this->declare_parameter("input_topic", std::string("/camera/image_raw"));
  output_topic_ =
      this->declare_parameter("output_topic", std::string("/camera/image_new"));
  output_width_ = this->declare_parameter("output_width", 640);
  output_height_ = this->declare_parameter("output_height", 480);
  interpolation_name_ =
      this->declare_parameter("interpolation", std::string("linear"));
  qos_reliability_ =
      this->declare_parameter("qos_reliability", std::string("best_effort"));

  if (output_width_ <= 0 || output_height_ <= 0) {
    throw std::invalid_argument(
        "output_width and output_height must be greater than zero");
  }

  interpolation_ = interpolation_from_string_(interpolation_name_);
}

void ImageResizerNode::initialize_io_()
{
  rclcpp::SensorDataQoS qos;
  if (qos_reliability_ == "reliable") {
    qos.reliable();
  } else if (qos_reliability_ == "best_effort") {
    qos.best_effort();
  } else {
    throw std::invalid_argument(
        "qos_reliability must be 'reliable' or 'best_effort'");
  }

  output_pub_ = image_transport::create_publisher(
      this, output_topic_, qos.get_rmw_qos_profile());

  input_sub_ = image_transport::create_subscription(
      this, input_topic_,
      std::bind(&ImageResizerNode::image_callback_, this, std::placeholders::_1),
      "raw", qos.get_rmw_qos_profile());

  RCLCPP_INFO(
      this->get_logger(),
      "Image resizer started: %s -> %s (%dx%d, interpolation=%s, qos=%s)",
      input_topic_.c_str(), output_topic_.c_str(), output_width_, output_height_,
      interpolation_name_.c_str(), qos_reliability_.c_str());
  RCLCPP_INFO(
      this->get_logger(),
      "Compressed stream available via image_transport plugin on %s/compressed",
      output_topic_.c_str());
}

void ImageResizerNode::image_callback_(
    const sensor_msgs::msg::Image::ConstSharedPtr& image_msg)
{
  try {
    const auto cv_type = cv_type_from_encoding_(image_msg->encoding);

    cv::Mat input(
        static_cast<int>(image_msg->height), static_cast<int>(image_msg->width),
        cv_type, const_cast<unsigned char*>(image_msg->data.data()),
        static_cast<size_t>(image_msg->step));

    cv::Mat resized;
    cv::resize(
        input, resized, cv::Size(output_width_, output_height_), 0.0, 0.0,
        interpolation_);

    if (!resized.isContinuous()) {
      resized = resized.clone();
    }

    sensor_msgs::msg::Image output_msg;
    output_msg.header = image_msg->header;
    output_msg.height = static_cast<uint32_t>(resized.rows);
    output_msg.width = static_cast<uint32_t>(resized.cols);
    output_msg.encoding = image_msg->encoding;
    output_msg.is_bigendian = image_msg->is_bigendian;
    output_msg.step =
        static_cast<sensor_msgs::msg::Image::_step_type>(resized.step);

    const auto byte_count = resized.total() * resized.elemSize();
    output_msg.data.resize(byte_count);
    std::memcpy(output_msg.data.data(), resized.data, byte_count);

    output_pub_.publish(output_msg);
  } catch (const std::exception& e) {
    RCLCPP_WARN(
        this->get_logger(), "Failed to resize image (%s): %s",
        image_msg->encoding.c_str(), e.what());
  }
}

int ImageResizerNode::interpolation_from_string_(
    const std::string& interpolation_name) const
{
  if (interpolation_name == "nearest") {
    return cv::INTER_NEAREST;
  }
  if (interpolation_name == "linear") {
    return cv::INTER_LINEAR;
  }
  if (interpolation_name == "area") {
    return cv::INTER_AREA;
  }
  if (interpolation_name == "cubic") {
    return cv::INTER_CUBIC;
  }
  throw std::invalid_argument(
      "interpolation must be one of: nearest, linear, area, cubic");
}

int ImageResizerNode::cv_type_from_encoding_(const std::string& encoding) const
{
  const auto channels = sensor_msgs::image_encodings::numChannels(encoding);
  const auto bit_depth = sensor_msgs::image_encodings::bitDepth(encoding);

  int cv_depth = CV_8U;
  switch (bit_depth) {
    case 8:
      cv_depth = CV_8U;
      break;
    case 16:
      cv_depth = CV_16U;
      break;
    case 32:
      cv_depth = CV_32F;
      break;
    default:
      throw std::invalid_argument(
          "Unsupported bit depth for encoding: " + encoding);
  }

  return CV_MAKETYPE(cv_depth, channels);
}
