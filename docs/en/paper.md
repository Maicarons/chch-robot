---
title: Academic Paper
---

# Academic Paper: Design and Implementation of a Xiangqi Human–Robot Chess System

This paper accompanies the documentation site and describes the CH-RO Xiangqi robot end to end:
vision-based board recognition, the Pikafish UCI decision engine, the five-value ASCII robot
protocol over STM32, and the Flask web interface. Typeset with XeLaTeX + ctex, references follow
GB/T 7714-2015. The paper includes vector figures (system architecture, recognition pipeline,
protocol sequence, board geometry), multiple data tables, and a real captured board photo.

## Downloads

- [Paper PDF (XeLaTeX, 15 pages)](/paper/chch-robot-paper.pdf)
- [LaTeX source](/paper/chch-robot-paper.tex)
- [Bibliography (.bib)](/paper/chch-robot-paper.bib)

## Overview

- **Perception:** RTMPose four-corner keypoints + perspective correction; a single full-board classifier outputs all 90 intersection classes (14 piece types + empty + unknown); multi-frame stabilization and rule-based move inference.
- **Cognition:** Pikafish (`UCI_Variant=xaingqi`) move selection; extended FEN board state.
- **Actuation:** five-value ASCII command `startX,startY,endX,endY,signal` over TCP 8086; STM32 kinematics with a `STATE:5,RESULT:1` completion handshake.
- **Interface:** Flask (port 5000) with live video, single/continuous recognition, and hardware/simulation dual modes.

## Notes

- The `author` field is a placeholder; replace with real authors and affiliations before publication.
- The experiments section reports only repository-verifiable specifications and test coverage. Empirical accuracy/latency on real hardware is left as future work and is not fabricated.
