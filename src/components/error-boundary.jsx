import React from "react";
import { Text, View } from "@tarojs/components";

export class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      message: ""
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error?.message || "页面运行时发生异常"
    };
  }

  componentDidCatch(error) {
    console.error("[JourneyRuntimeError]", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View className="runtime-error-shell">
          <View className="section-card">
            <Text className="section-title">页面暂时不可用</Text>
            <Text className="section-desc">我们已经拦截了这次运行时异常，避免直接白屏。</Text>
            <Text className="error-text">{this.state.message}</Text>
            <Text className="hint-text">请返回上一页或重新进入当前页面。</Text>
          </View>
        </View>
      );
    }

    return this.props.children;
  }
}
