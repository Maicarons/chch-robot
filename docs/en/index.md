---
layout: home
hero:
  name: CH-RO Robot
  text: Xiangqi robot documentation
  tagline: Vision recognition, Pikafish AI, STM32 motion control, and a Flask control console.
  image:
    src: /hero.svg
    alt: CH-RO Robot Team
  actions:
    - theme: brand
      text: English
      link: /en/
    - theme: alt
      text: 中文
      link: /zh/
features:
  - title: Vision board recognition
    details: RTMPose corner keypoints with perspective correction; one global classifier outputs all 90 intersections at once. Multi-frame stabilization and rule-based dynamic move inference.
  - title: Pikafish AI engine
    details: UCI_Variant=xaingqi move generation over an extended FEN board representation, driving both hardware and simulation play.
  - title: STM32 motion control
    details: Five-value ASCII command protocol over TCP 8086, on-MCU kinematics, and a STATE/RESULT handshake with homing.
  - title: Flask web console
    details: Live camera stream, single/continuous recognition, and a hardware/simulation dual-mode play UI.
---
