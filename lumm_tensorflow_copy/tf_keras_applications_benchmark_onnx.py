"""
Copyright 2019 Lummetry.AI (Knowledge Investment Group SRL). All Rights Reserved.
* NOTICE:  All information contained herein is, and remains
* the property of Knowledge Investment Group SRL.  
* The intellectual and technical concepts contained
* herein are proprietary to Knowledge Investment Group SRL
* and may be covered by Romanian and Foreign Patents,
* patents in process, and are protected by trade secret or copyright law.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Knowledge Investment Group SRL.
@copyright: Lummetry.AI
@author: Lummetry.AI
@project: 
@description:
"""
import os
import cv2
import numpy as np
import pandas as pd
import tensorflow as tf

from time import time
from libraries import Logger
from data_gen import data_generator
from lumm_tensorflow.tf_keras_applications import get_tf_keras_application_model, MODELS
from lumm_tensorflow.utils import load_onnx_model, benchmark_onnx_model


if __name__ == '__main__':
  log = Logger(
    lib_name='BENCHMARK', 
    config_file='config.txt',
    TF_KERAS=False
    )
  
  BATCH_SIZE = 1
  N_WARMUP = 10
  N_ITERS = 10
  
  log.p('Tensorflow version: {}'.format(tf.__version__))
  
  path_images = os.path.join(log.get_data_subfolder('General'))
  lst_imgs = [os.path.join(path_images, x) for x in os.listdir(path_images)]
  lst_imgs = [cv2.imread(x) for x in lst_imgs]
  np_imgs = np.array(lst_imgs)
  
  dct_times = {}
  for model_name, resize in MODELS.items():
    model, ort_sess, inputs, outputs = load_onnx_model(log, model_name)
    log.p('Benchmarking {}'.format(model_name))
    preds, lst_time = benchmark_onnx_model(
      log=log, 
      ort_sess=ort_sess, 
      input_name=inputs[0],
      np_imgs_bgr=np_imgs, 
      batch_size=BATCH_SIZE, 
      n_warmup=N_WARMUP, 
      n_iters=N_ITERS,
      as_rgb=True,
      resize=resize
      )
    dct_times[model_name] = lst_time
  #endfor
  
  df = pd.DataFrame(dct_times)
  log.p('\n\n{}'.format(df))
  platform, system = log.get_platform()
  log.save_dataframe(
    df=df,
    fn='{}_{}_{}.csv'.format(platform, 'tf_keras_applications_onnx', log.now_str()),
    folder='output'
    )