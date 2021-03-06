import torch as th
import numpy as np

from time import time
from data import data_generator

DEVICE = th.device('cuda:0' if th.cuda.is_available() else 'cpu')

def prepare_data(log, np_batch, resize, as_rgb, to_nchw, 
                 preprocess_input_fn=None, normalize=False):
  batch = np_batch
  if resize:
    batch = np.array([log.center_image2(x, resize[0], resize[1]) for x in batch])
  if as_rgb:
    batch = np.array([x[:,:,::-1] for x in batch])
  if preprocess_input_fn:
    lst = [preprocess_input_fn(x) for x in batch]
    if isinstance(lst[0], (np.ndarray)):
      batch = np.array(lst)
    elif isinstance(lst[0], (th.Tensor)):
      batch = [x.unsqueeze(0) for x in lst]
      batch = th.cat(batch, axis=0)
  if normalize:
    batch = batch / 255
  if to_nchw:
    batch = np.transpose(batch, (0, 3, 1, 2))
  if isinstance(batch, np.ndarray):
    batch = batch.astype('float32')
  elif isinstance(batch, th.Tensor):
    batch = batch.type(th.float32)
  return batch

def predict(predict_method, data_gen):  
  lst_time = []
  lst_preds = []
  for np_batch in data_gen:
    start = time()
    preds = predict_method(np_batch)
    stop = time()
    lst_time.append((stop - start) / len(np_batch))
    lst_preds.append(preds)
  return lst_preds, lst_time


#TENSORFLOW
def benchmark_keras_model(log, n_warmup, n_iters, model, np_imgs_bgr, batch_size, 
                          as_rgb=False, resize=None, preprocess_input_fn=None, normalize=False):
  def _predict_method(np_batch):
    np_batch = prepare_data(
      log=log,
      np_batch=np_batch,
      resize=resize,
      as_rgb=as_rgb,
      to_nchw=False,
      preprocess_input_fn=preprocess_input_fn,
      normalize=normalize
      )
    preds = model.predict(np_batch)
    return preds
  
  #warmup
  for i in range(1, n_warmup+1):
    log.p(' Warmup {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  #iters
  for i in range(1, n_iters+1):
    log.p(' Iter {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    lst_preds, lst_time = predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
    
  return lst_preds, lst_time


def benchmark_vapor_graph(log, n_warmup, n_iters, graph, np_imgs_bgr, batch_size, 
                          as_rgb=False, normalize=False):
  def _predict_method(np_batch):
    np_batch = prepare_data(
      log=log,
      np_batch=np_batch,
      as_rgb=as_rgb,
      resize=None,
      to_nchw=False,
      normalize=normalize
      )
    return graph.predict(np_batch)
  
  #warmup
  for i in range(1, n_warmup+1):
    log.p(' Warmup {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  #iters
  for i in range(1, n_iters+1):
    log.p(' Iter {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    lst_preds, lst_time = predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  return lst_preds, lst_time


def benchmark_tf_graph(log, n_warmup, n_iters, sess, tf_inp, tf_out, 
                       np_imgs_bgr, batch_size, as_rgb=False, resize=None,
                       preprocess_input_fn=None, normalize=False):
  #avoid collision with automl_effdet that requires eager execution
  import tensorflow.compat.v1 as tf
  tf.disable_eager_execution()
  tf_runoptions = tf.RunOptions(report_tensor_allocations_upon_oom=True)

  def _predict_method(np_batch):
    np_batch = prepare_data(
      log=log,
      np_batch=np_batch,
      as_rgb=as_rgb,
      resize=resize,
      to_nchw=False,
      normalize=normalize,
      preprocess_input_fn=preprocess_input_fn
      )
    out_scores = sess.run(
      tf_out,
      feed_dict={tf_inp: np_batch},
      options=tf_runoptions
      )
    return out_scores
  
  #warmup
  for i in range(1, n_warmup+1):
    log.p(' Warmup {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  #iters
  for i in range(1, n_iters+1):
    log.p(' Iter {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    lst_preds, lst_time = predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  #endfor
  return lst_preds, lst_time

#PYTORCH
def benchmark_pytorch_model(log, n_warmup, n_iters, model, np_imgs_bgr, batch_size, 
                          as_rgb=False, resize=None, to_nchw=False, preprocess_input_fn=None, normalize=False):
  def _predict_method(np_batch):
    batch = prepare_data(
      log=log,
      np_batch=np_batch,
      resize=resize,
      as_rgb=as_rgb,
      to_nchw=to_nchw,
      preprocess_input_fn=preprocess_input_fn,
      normalize=normalize
      )
    with th.no_grad():
      if isinstance(batch, np.ndarray):
        th_x = th.from_numpy(batch).to(DEVICE)
      th_x = batch.to(DEVICE)
      preds = model(th_x).cpu().numpy()
    return preds
  
  #warmup
  for i in range(1, n_warmup+1):
    log.p(' Warmup {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  #iters
  for i in range(1, n_iters+1):
    log.p(' Iter {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    lst_preds, lst_time = predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  #endfor
  
  return lst_preds, lst_time


def benchmark_pytorch_effdet_model(log, n_warmup, n_iters, model, np_imgs_bgr, batch_size, 
                                 as_rgb=False, to_nchw=False, normalize=False):
  def _predict_method(np_batch):
    np_batch = prepare_data(
      log=log,
      np_batch=np_batch,
      resize=resize,
      as_rgb=as_rgb,
      to_nchw=to_nchw,
      normalize=normalize
      )
    with th.no_grad():
      th_x = th.from_numpy(np_batch).to(DEVICE)
      output = model(th_x).cpu().numpy()
      results = []
      for index, sample in enumerate(output):
        image_id = i
        sample[:, 2] -= sample[:, 0]
        sample[:, 3] -= sample[:, 1]
        for det in sample:
          score = float(det[4])
          if score < .001:  # stop when below this threshold, scores in descending order
              break
          coco_det = dict(
              image_id=image_id,
              bbox=det[0:4].tolist(),
              score=score,
              category_id=int(det[5]))
          results.append(coco_det)
      #endfor
    #end with
    return

  input_size = model.config.image_size
  resize = input_size
  # param_count = sum([m.numel() for m in model.parameters()])
  # print('Model %s created, param count: %d' % (model_name, param_count))
  
  #warmup
  for i in range(1, n_warmup+1):
    log.p(' Warmup {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  #iters
  for i in range(1, n_iters+1):
    log.p(' Iter {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    lst_preds, lst_time = predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  #endfor
  
  return lst_preds, lst_time


def benchmark_torch_hub_model(log, n_warmup, n_iters, model, np_imgs_bgr, batch_size, 
                              as_rgb=False, resize=None, to_nchw=False, normalize=False):
  def _predict_method(np_batch):
    np_batch = prepare_data(
      log=log,
      np_batch=np_batch,
      resize=resize,
      as_rgb=as_rgb,
      to_nchw=to_nchw,
      normalize=normalize
      )
    with th.no_grad():
      th_x = th.from_numpy(np_batch).to(DEVICE)
      th_preds = model(th_x)
      p1 = th_preds[0].cpu().numpy()
      p2 = [x.cpu().numpy() for x in th_preds[1]]
      preds = (p1, p2)
    return preds
  
  #warmup
  for i in range(1, n_warmup+1):
    log.p(' Warmup {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  #iters
  for i in range(1, n_iters+1):
    log.p(' Iter {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    lst_preds, lst_time = predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  #endfor
  
  return lst_preds, lst_time


#TENSORFLOW / PYTORCH
def benchmark_onnx_model(log, n_warmup, n_iters, ort_sess, input_name, np_imgs_bgr, 
                         batch_size, as_rgb=False, resize=None, to_nchw=False,
                         preprocess_input_fn=None, normalize=False):
  def _predict_method(np_batch):
    np_batch = prepare_data(
      log=log,
      np_batch=np_batch,
      resize=resize,
      as_rgb=as_rgb,
      to_nchw=to_nchw,
      preprocess_input_fn=preprocess_input_fn,
      normalize=normalize
      )
    if isinstance(np_batch, th.Tensor):
      np_batch = np.array(np_batch)
    preds = ort_sess.run(
      output_names=None, 
      input_feed={input_name: np_batch}
      )
    return preds
  #enddef
  
  #warmup
  for i in range(1, n_warmup+1):
    log.p(' Warmup {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  #iters
  for i in range(1, n_iters+1):
    log.p(' Iter {}'.format(i))
    gen = data_generator(np_imgs=np_imgs_bgr, batch_size=batch_size)
    lst_preds, lst_time = predict(predict_method=_predict_method, data_gen=gen)
    log.p(' Done', show_time=True)
  
  return lst_preds, lst_time