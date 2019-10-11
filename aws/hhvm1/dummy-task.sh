#!/bin/bash

SEC=$((RANDOM % 30 + 10))

echo "Pretending to do work for $SEC seconds..."
sleep $SEC
