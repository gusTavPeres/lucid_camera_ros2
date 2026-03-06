#include "ImageResizerNode.h"

int main(int argc, char* argv[])
{
  rclcpp::init(argc, argv);
  {
    rclcpp::NodeOptions options;
    options.use_intra_process_comms(true);
    auto node = std::make_shared<ImageResizerNode>(options);
    rclcpp::spin(node);
  }
  rclcpp::shutdown();
  return 0;
}
