import config

import numpy as np
import numpy.linalg as LA

from src.attackers.fast_gradient import FastGradientMethod
import tensorflow as tf

supported_methods = {"fgsm": {"class": FastGradientMethod,
                              "params": {"eps_step": 0.1, "eps_max": 1., "clip_min": 0., "clip_max": 1.}},
                      # "jsma": {"class": SaliencyMapMethod,
                      #          "params": {"theta": 1., "gamma": 0.01, "clip_min": 0., "clip_max": 1.}}
                      }


def get_crafter(method, classifier, session, params=None):

    try:
        crafter = supported_methods[method]["class"](classifier, sess=session)
    except:
        raise NotImplementedError("{} crafting method not supported.".format(method))

    if params:
        crafter.set_params(**params)
    else:
        crafter.set_params(**supported_methods[method]["params"])

    return crafter

def empirical_robustness_df(x, adv_x, model, sess):
    """ Computes the Empirical Robustness of a `model` over the sample `x` for a given adversarial crafting method 
    `method_name`, following https://arxiv.org/abs/1511.04599
    
    :param x: 
    :param model: 
    :param method_name: 
    :param sess: 
    :param method_params: 
    :return: 
    """

    # predict the labels for adversarial examples
    y = model.predict(x,verbose=0)
    y_pred = model.predict(adv_x,verbose=0)

    idxs = ((np.argmax(y_pred,axis=1) != np.argmax(y,axis=1)))
    assert np.sum(idxs) != 0.0
    print(np.sum(idxs),len(idxs))

    perts_norm = LA.norm((adv_x-x).reshape(x.shape[0], -1), ord=2, axis=1)
    print(np.mean(perts_norm))
    perts_norm = perts_norm[idxs]
    print(np.mean(perts_norm))
    print(np.mean(LA.norm(x[idxs].reshape(np.sum(idxs), -1), ord=2, axis=1)))
    return np.mean(perts_norm/LA.norm(x[idxs].reshape(np.sum(idxs), -1), ord=2, axis=1))


def empirical_robustness(x, classifier, sess, method_name, method_params=None):
    """ Computes the Empirical Robustness of a `classifier` over the sample `x` for a given adversarial crafting method 
    `method_name`, following https://arxiv.org/abs/1511.04599
    
    :param x: 
    :param classifier: 
    :param method_name: 
    :param sess: 
    :param method_params: 
    :return: 
    """

    crafter = get_crafter(method_name, classifier, sess, method_params)
    adv_x = crafter.generate(x, minimal=True, **method_params)

    # predict the labels for adversarial examples
    y = classifier.predict(x,verbose=0)
    y_pred = classifier.predict(adv_x,verbose=0)

    idxs = ((np.argmax(y_pred,axis=1) != np.argmax(y,axis=1)))
    if np.sum(idxs) == 0.0:
        return 0

    perts_norm = LA.norm((adv_x-x).reshape(x.shape[0], -1), ord=crafter.ord, axis=1)
    perts_norm = perts_norm[idxs]

    return np.mean(perts_norm/LA.norm(x[idxs].reshape(np.sum(idxs), -1), ord=crafter.ord, axis=1))


def kernel_rbf(x,y,sigma=0.1):
    """Computes the kernel 

    :param x: a tensor object or a numpy array
    :param y: a tensor object or a numpy array

    returns: a tensor object
    """
    norms_x = tf.reduce_sum(x ** 2, 1)[:, None] # axis = [1] for later tf vrsions
    norms_y = tf.reduce_sum(y ** 2, 1)[None, :]
    dists = norms_x - 2 * tf.matmul(x, y, transpose_b=True) + norms_y
    return tf.exp(-(1.0/(2.0*sigma)*dists))

def euclidean_dist(x,y):
    """Computes the kernel 

    :param x: a tensor object or a numpy array
    :param y: a tensor object or a numpy array

    returns: a tensor object
    """
    norms_x = tf.reduce_sum(x ** 2, 1)[:, None] # axis = [1] for later tf vrsions
    norms_y = tf.reduce_sum(y ** 2, 1)[None, :]
    dists = norms_x - 2 * tf.matmul(x, y, transpose_b=True) + norms_y
    return dists 



def mmd(x_data,y_data,sess,sigma=0.1):
    """ Computes Maximum Mean Disrepancy between x and y

    :param x_data: numpy array
    :param y_data: numpy array

    returns: a float value corresponding to mmd(x_data,y_data)
    """
    assert x_data.shape[0]==y_daya.shape[0]
    x_data = x_data.reshape(x_data.shape[0],np.prod(x_data.shape[1:]))
    y_data = y_data.reshape(y_data.shape[0],np.prod(y_data.shape[1:]))
    x = tf.placeholder(tf.float32, shape=x_data.shape)
    y = tf.placeholder(tf.float32, shape=y_data.shape)
    mmd = tf.reduce_sum(kernel_rbf(x,x)) - \
            2.0*tf.reduce_sum(kernel_rbf(x,y)) + tf.reduce_sum(kernel_rbf(y,y))
    
    return sess.run(mmd, feed_dict = {x:x_data, y:y_data})


def mmd_metric(x, classifier, sess, method_name, method_params=None):
    """ 
    
    """
    crafter = get_crafter(method_name, classifier, sess, method_params)
    adv_x = crafter.generate(x, minimal=True, **method_params)

    return mmd(x,adv_x,sess)


def nearest_nieghbour_dist(x, y_true, classifier, x_train,  sess, method_name, method_params=None):
    """
    Nearest Neighbour distance
    """
    
    # craft the adversarial examples
    crafter = get_crafter(method_name, classifier, sess, method_params)
    adv_x = crafter.generate(x.copy(), minimal=True,**method_params)

    # predict the labels for adversarial examples
    
    y_pred = classifier.predict(adv_x,verbose=0)
    y_pred_2 = classifier.predict(x,verbose=0)
    idxs = ((np.argmax(y_pred,axis=1) == np.argmax(y,axis=1)))
    idxs2 = ((np.argmax(y_pred,axis=1) == np.argmax(y_pred_2,axis=1)))
    print('Flips wrt: true ',np.sum(idxs),' pred ',np.sum(idxs2))
    
    return classifier.evaluate(adv_x,y)[1]*100

def nearest_nieghbour_dist(x, classifier, x_train,  sess, method_name, method_params=None):

    """
    Nearest Neighbour distance
    """

    # craft the adversarial examples
    crafter = get_crafter(method_name, classifier, sess, method_params)
    adv_x = crafter.generate(x, minimal=True,**method_params)

    # predict the labels for adversarial examples
    y_pred = classifier.predict(adv_x,verbose=0)

    dists = np.min(sess.run(dists),1)/LA.norm(x.reshape(x.shape[0], -1), ord=2, axis=1) 
    idxs = ((np.argmax(y_pred,axis=1) != np.argmax(y,axis=1)))
    avg_nn_dist = np.mean(dists[idxs])

    return avg_nn_dist


def nearest_nieghbour_dist_df(x,adv_x, classifier, x_train,  sess):

    """
    Nearest Neighbour distance
    """


    # predict the labels for adversarial examples
    y = classifier.predict(x,verbose=0)
    y_pred = classifier.predict(adv_x,verbose=0)
 
    adv_x_ = adv_x.reshape(adv_x.shape[0],np.prod(adv_x.shape[1:]))
    x_  = x_train.reshape(x_train.shape[0],np.prod(x_train.shape[1:]))
    dists = euclidean_dist(adv_x_,x_)

    dists = np.min(sess.run(dists),1)/LA.norm(x.reshape(x.shape[0], -1), ord=2, axis=1) 
    idxs = ((np.argmax(y_pred,axis=1) != np.argmax(y,axis=1)))

    avg_nn_dist = np.mean(dists[idxs])

    return avg_nn_dist

def stoch_preds(x,classifier,sess):
    """
    TODO 
    """
    y = classifier(x)
    if x.shape[0] <= 100:
        pass
    else:
        #run batch
        pass

def mc_drop(x, classifier, sess, method_name, method_params=None):

    '''
    TODO
    droptout at test time for the crafted adversarial examples
    '''
   
    crafter = get_crafter(method_name, classifier, sess, method_params)
    adv_x = crafter.generate(x, minimal=True, **method_params)

    pass
    
