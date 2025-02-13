from keras.datasets import mnist
import time
from utils import *
from scipy.misc import imsave as ims
from ops import *
from utils import *
from Utlis2 import *
import random as random
from glob import glob
import os, gzip
import keras as keras
from glob import glob
from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D
from keras import backend as K

os.environ['CUDA_VISIBLE_DEVICES']='6'

from mnist_hand import *
from Basic_structure import *
from CIFAR10 import *

z_dim = 100

def Code_Classifier(s, scopename, n_hidden, n_output, keep_prob, reuse=False):
    with tf.variable_scope(scopename, reuse=reuse):
        input = s

        # initializers
        w_init = tf.contrib.layers.variance_scaling_initializer()
        b_init = tf.constant_initializer(0.)

        # 1st hidden layer
        w0 = tf.get_variable('w0', [input.get_shape()[1], n_hidden], initializer=w_init)
        b0 = tf.get_variable('b0', [n_hidden], initializer=b_init)
        h0 = tf.matmul(s, w0) + b0
        h0 = tf.nn.tanh(h0)
        h0 = tf.nn.dropout(h0, keep_prob)

        n_output = 4
        # output layer-mean
        wo = tf.get_variable('wo', [h0.get_shape()[1], n_output], initializer=w_init)
        bo = tf.get_variable('bo', [n_output], initializer=b_init)
        y1 = tf.matmul(h0, wo) + bo
        y = tf.nn.softmax(y1)

    return y1,y

def file_name(file_dir):
    t1 = []
    file_dir = "F:/Third_Experiment/Multiple_GAN_codes/data/images_background/"
    for root, dirs, files in os.walk(file_dir):
        for a1 in dirs:
            b1 = "F:/Third_Experiment/Multiple_GAN_codes/data/images_background/" + a1 + "/renders/*.png"
            b1 = "F:/Third_Experiment/Multiple_GAN_codes/data/images_background/" + a1
            for root2, dirs2, files2 in os.walk(b1):
                for c1 in dirs2:
                    b2 = b1 + "/" + c1 + "/*.png"
                    img_path = glob(b2)
                    t1.append(img_path)

        print('root_dir:', root)  # 当前目录路径
        print('sub_dirs:', dirs)  # 当前路径下所有子目录
        print('files:', files)  # 当前路径下所有非目录子文件

    cc = []

    for i in range(len(t1)):
        a1 = t1[i]
        for p1 in a1:
            cc.append(p1)
    return cc

def sample_gumbel(shape, eps=1e-20):
    """Sample from Gumbel(0, 1)"""
    U = tf.random_uniform(shape, minval=0, maxval=1)
    return -tf.log(-tf.log(U + eps) + eps)

def my_gumbel_softmax_sample(logits, cats_range, temperature=0.1):
    """ Draw a sample from the Gumbel-Softmax distribution"""
    y = logits + sample_gumbel(tf.shape(logits))
    logits_with_noise = tf.nn.softmax(y / temperature)
    return logits_with_noise

def load_mnist(dataset_name):
    data_dir = os.path.join("./data", dataset_name)

    def extract_data(filename, num_data, head_size, data_size):
        with gzip.open(filename) as bytestream:
            bytestream.read(head_size)
            buf = bytestream.read(data_size * num_data)
            data = np.frombuffer(buf, dtype=np.uint8).astype(np.float)
        return data

    data = extract_data(data_dir + '/train-images-idx3-ubyte.gz', 60000, 16, 28 * 28)
    trX = data.reshape((60000, 28, 28, 1))

    data = extract_data(data_dir + '/train-labels-idx1-ubyte.gz', 60000, 8, 1)
    trY = data.reshape((60000))

    data = extract_data(data_dir + '/t10k-images-idx3-ubyte.gz', 10000, 16, 28 * 28)
    teX = data.reshape((10000, 28, 28, 1))

    data = extract_data(data_dir + '/t10k-labels-idx1-ubyte.gz', 10000, 8, 1)
    teY = data.reshape((10000))

    trY = np.asarray(trY)
    teY = np.asarray(teY)

    X = np.concatenate((trX, teX), axis=0)
    y = np.concatenate((trY, teY), axis=0).astype(np.int)

    seed = 547
    np.random.seed(seed)
    np.random.shuffle(X)
    np.random.seed(seed)
    np.random.shuffle(y)

    y_vec = np.zeros((len(y), 10), dtype=np.float)
    for i, label in enumerate(y):
        y_vec[i, y[i]] = 1.0

    return X / 255., y_vec

def My_Encoder_mnist(image, name, batch_size=64, reuse=False):
    with tf.variable_scope(name) as scope:
        if reuse:
            scope.reuse_variables()
        len_discrete_code = 4

        is_training = True
        z_dim = 100
        x = image
        net = lrelu(conv2d(x, 64, 4, 4, 2, 2, name='c_conv1'))
        net = lrelu(bn(conv2d(net, 128, 4, 4, 2, 2, name='c_conv2'), is_training=is_training, scope='c_bn2'))
        net = tf.reshape(net, [batch_size, -1])
        net = lrelu(bn(linear(net, 1024, scope='c_fc3'), is_training=is_training, scope='c_bn3'))

        net = lrelu(bn(linear(net, 64, scope='e_fc11'), is_training=is_training, scope='c_bn11'))

        z_mean = linear(net, z_dim, 'e_mean')
        z_log_sigma_sq = linear(net, z_dim, 'e_log_sigma_sq')
        z_log_sigma_sq = tf.nn.softplus(z_log_sigma_sq)

        return z_mean, z_log_sigma_sq

def My_Classifier_mnist(image, name, batch_size=64, reuse=False):
    with tf.variable_scope(name) as scope:
        if reuse:
            scope.reuse_variables()
        len_discrete_code = 4

        is_training = True
        z_dim = 32
        x = image
        net = lrelu(conv2d(x, 64, 4, 4, 2, 2, name='c_conv1'))
        net = lrelu(bn(conv2d(net, 128, 4, 4, 2, 2, name='c_conv2'), is_training=is_training, scope='c_bn2'))
        net = tf.reshape(net, [batch_size, -1])
        net = lrelu(bn(linear(net, 1024, scope='c_fc3'), is_training=is_training, scope='c_bn3'))

        net = lrelu(bn(linear(net, 64, scope='e_fc11'), is_training=is_training, scope='c_bn11'))

        out_logit = linear(net, len_discrete_code, scope='e_fc22')
        softmaxValue = tf.nn.softmax(out_logit)

        return out_logit, softmaxValue

def MINI_Classifier(s, scopename,reuse=False):
    keep_prob = 1.0
    with tf.variable_scope(scopename, reuse=reuse):
        input = s
        n_output = 10
        n_hidden = 500
        # initializers
        w_init = tf.contrib.layers.variance_scaling_initializer()
        b_init = tf.constant_initializer(0.)

        # 1st hidden layer
        w0 = tf.get_variable('w0', [input.get_shape()[1], n_hidden], initializer=w_init)
        b0 = tf.get_variable('b0', [n_hidden], initializer=b_init)
        h0 = tf.matmul(s, w0) + b0
        h0 = tf.nn.tanh(h0)
        h0 = tf.nn.dropout(h0, keep_prob)

        n_output = 10
        # output layer-mean
        wo = tf.get_variable('wo', [h0.get_shape()[1], n_output], initializer=w_init)
        bo = tf.get_variable('bo', [n_output], initializer=b_init)
        y1 = tf.matmul(h0, wo) + bo
        y = tf.nn.softmax(y1)

    return y1,y

# Create model of CNN with slim api
def Image_classifier(inputs,scopename, is_training=True,reuse=False):
    with tf.variable_scope(scopename, reuse=reuse):
        batch_norm_params = {'is_training': is_training, 'decay': 0.9, 'updates_collections': None}
        with slim.arg_scope([slim.conv2d, slim.fully_connected],
                            normalizer_fn=slim.batch_norm,
                            normalizer_params=batch_norm_params):
            #x = tf.reshape(inputs, [-1, 28, 28, 1])
            x = tf.reshape(inputs, [-1, 32, 32, 3])

            # For slim.conv2d, default argument values are like
            # normalizer_fn = None, normalizer_params = None, <== slim.arg_scope changes these arguments
            # padding='SAME', activation_fn=nn.relu,
            # weights_initializer = initializers.xavier_initializer(),
            # biases_initializer = init_ops.zeros_initializer,
            net = slim.conv2d(x, 32, [5, 5], scope='conv1')
            net = slim.max_pool2d(net, [2, 2], scope='pool1')
            net = slim.conv2d(net, 64, [5, 5], scope='conv2')
            net = slim.max_pool2d(net, [2, 2], scope='pool2')
            net = slim.flatten(net, scope='flatten3')

            # For slim.fully_connected, default argument values are like
            # activation_fn = nn.relu,
            # normalizer_fn = None, normalizer_params = None, <== slim.arg_scope changes these arguments
            # weights_initializer = initializers.xavier_initializer(),
            # biases_initializer = init_ops.zeros_initializer,
            net = slim.fully_connected(net, 1024, scope='fc3')
            net = slim.dropout(net, is_training=is_training, scope='dropout3')  # 0.5 by default
            outputs = slim.fully_connected(net, 10, activation_fn=None, normalizer_fn=None, scope='fco')
    return outputs

class LifeLone_MNIST(object):
    def __init__(self):
        self.batch_size = 64
        self.input_height = 32
        self.input_width = 32
        self.c_dim = 3
        self.z_dim = 100
        self.len_discrete_code = 4
        self.epoch = 30

        self.learning_rate = 0.0002
        self.beta1 = 0.5

        # MNIST dataset
        mnistName = "mnist"
        fashionMnistName = "Fashion"

        mnist_train_x, mnist_train_label, mnist_test, mnist_label_test, x_train, y_train, x_test, y_test = GiveMNIST_SVHN()

        self.mnist_train_x = mnist_train_x
        self.mnist_train_y = np.zeros((np.shape(x_train)[0], 4))
        self.mnist_train_y[:, 0] = 1
        self.mnist_label = mnist_train_label
        self.mnist_label_test = mnist_label_test
        self.mnist_test_x = mnist_test
        self.mnist_test_y = np.zeros((np.shape(mnist_test)[0], 4))
        self.mnist_test_y[:, 0] = 1

        self.svhn_train_x = x_train
        self.svhn_train_y = np.zeros((np.shape(x_train)[0], 4))
        self.svhn_train_y[:, 1] = 1
        self.svhn_label = y_train
        self.svhn_label_test = y_test
        self.svhn_test_x = x_test
        self.svhn_test_y = np.zeros((np.shape(x_test)[0], 4))
        self.svhn_test_y[:, 1] = 1

        self.cifar_train_x, self.cifar_train_label, self.cifar_test_x, self.cifar_test_label = prepare_data()
        # self.cifar_train_x, self.cifar_test_x = color_preprocessing(self.cifar_train_x, self.cifar_test_x)
        self.cifar_train_x = (self.cifar_train_x - 127.5) / 127.5
        self.cifar_test_x = (self.cifar_test_x - 127.5) / 127.5
        self.CifarTrain_y = np.zeros((np.shape(self.cifar_train_x)[0], 4))
        self.CifarTrain_y[:, 2] = 1

    def build_model(self):
        min_value = 1e-10
        # some parameters
        image_dims = [self.input_height, self.input_width, self.c_dim]
        bs = self.batch_size
        self.inputs = tf.placeholder(tf.float32, [bs] + image_dims, name='real_images')
        self.z = tf.placeholder(tf.float32, [self.batch_size, self.z_dim], name='z')
        self.y = tf.placeholder(tf.float32, [self.batch_size, self.len_discrete_code])
        self.labels = tf.placeholder(tf.float32, [self.batch_size, 10])
        self.gan_domain = tf.placeholder(tf.float32, [self.batch_size, 4])

        # GAN networks
        gan_code = tf.concat((self.z, self.y), axis=1)
        G1 = Generator_SVHN("GAN_generator", gan_code, reuse=False)

        ## 1. GAN Loss
        # output of D for real images
        D_real, D_real_logits, _ = Discriminator_SVHN(self.inputs, "discriminator", reuse=False)

        # output of D for fake images
        D_fake, D_fake_logits, input4classifier_fake = Discriminator_SVHN(G1, "discriminator", reuse=True)

        self.g_loss = tf.reduce_mean(D_fake_logits)
        self.d_loss = tf.reduce_mean(D_real_logits) - tf.reduce_mean(D_fake_logits)

        epsilon = tf.random_uniform([], 0.0, 1.0)
        x_hat = epsilon * self.inputs + (1 - epsilon) * G1
        _, d_hat, _ = Discriminator_SVHN(x_hat, "discriminator", reuse=True)
        scale = 10.0
        ddx = tf.gradients(d_hat, x_hat)[0]
        ddx = tf.sqrt(tf.reduce_sum(tf.square(ddx), axis=1))
        ddx = tf.reduce_mean(tf.square(ddx - 1.0) * scale)
        self.d_loss = self.d_loss + ddx

        self.isPhase = 0

        # domain 1
        # domain 1
        z_mean, z_log_sigma_sq = My_Encoder_mnist(self.inputs, "encoder1", batch_size=64, reuse=False)
        out_logit, softmaxValue = My_Classifier_mnist(self.inputs, "classifier", batch_size=64, reuse=False)

        continous_variables = z_mean + z_log_sigma_sq * tf.random_normal(tf.shape(z_mean), 0, 1, dtype=tf.float32)

        # define the classifier
        label_logits = Image_classifier(self.inputs, "Mini_classifier", reuse=False)
        self.mini_classLoss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=label_logits, labels=self.labels))

        log_y = tf.log(softmaxValue + 1e-10)
        discrete_real = my_gumbel_softmax_sample(log_y, np.arange(self.len_discrete_code))

        log_y2 = tf.log(tf.nn.softmax(label_logits) + 1e-10)
        discrete_real2 = my_gumbel_softmax_sample(log_y2, np.arange(10))

        y_labels = tf.argmax(softmaxValue, 1)
        y_labels = tf.cast(y_labels, dtype=tf.float32)
        y_labels = tf.reshape(y_labels, (-1, 1))

        code1 = tf.concat((continous_variables, discrete_real, discrete_real2), axis=1)
        reco1 = Generator_SVHN("generator1", code1, reuse=False)
        reco2 = reco1
        self.Reco = reco1

        # classification loss
        self.classifier_loss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=out_logit, labels=self.y))
        self.mini_classLoss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=label_logits, labels=self.labels))

        # VAE loss
        reconstruction_loss1 = tf.reduce_mean(tf.reduce_sum(tf.square(reco1 - self.inputs), [1, 2, 3]))

        KL_divergence1 = 0.5 * tf.reduce_sum(
            tf.square(z_mean-y_labels) + tf.square(z_log_sigma_sq) - tf.log(1e-8 + tf.square(z_log_sigma_sq)) - 1, 1)
        KL_divergence1 = tf.reduce_mean(KL_divergence1)

        self.vae_loss1 = reconstruction_loss1 + KL_divergence1

        self.vaeLoss = self.vae_loss1

        """ Training """
        # divide trainable variables into a group for D and a group for G
        T_vars = tf.trainable_variables()
        encoder_vars1 = [var for var in T_vars if var.name.startswith('encoder1')]
        generator1_vars = [var for var in T_vars if var.name.startswith('generator1')]
        discriminator_vars1 = [var for var in T_vars if var.name.startswith('discriminator')]
        GAN_generator_vars = [var for var in T_vars if var.name.startswith('GAN_generator')]
        Codeencoder_vars1 = [var for var in T_vars if var.name.startswith('classifier')]
        classifier_vars1 = [var for var in T_vars if var.name.startswith('Mini_classifier')]

        self.output1 = reco1
        self.output2 = reco2
        self.GAN_output = G1

        # optimizers
        with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
            self.vae1_optim = tf.train.AdamOptimizer(self.learning_rate, beta1=self.beta1) \
                .minimize(self.vaeLoss, var_list=encoder_vars1 + generator1_vars + classifier_vars1+Codeencoder_vars1)
            self.d_optim = tf.train.AdamOptimizer(self.learning_rate, beta1=self.beta1) \
                .minimize(self.d_loss, var_list=discriminator_vars1)
            self.g_optim = tf.train.AdamOptimizer(self.learning_rate * 5, beta1=self.beta1) \
                .minimize(self.g_loss, var_list=GAN_generator_vars)
            self.domain_optim = tf.train.AdamOptimizer(self.learning_rate, beta1=self.beta1) \
                .minimize(self.classifier_loss, var_list=Codeencoder_vars1)
            self.classifier_optim = tf.train.AdamOptimizer(self.learning_rate, beta1=self.beta1) \
                .minimize(self.mini_classLoss, var_list=classifier_vars1)
        b1 = 0

    def Make_DomainPredictions(self,testX):
        # domain 1
        z_mean, z_log_sigma_sq = My_Encoder_mnist(self.inputs, "encoder1", batch_size=64, reuse=True)

        continous_variables = z_mean + z_log_sigma_sq * tf.random_normal(tf.shape(z_mean), 0, 1, dtype=tf.float32)

        # define code classifier
        code_predLogit, code_pred = My_Classifier_mnist(self.inputs, "classifier", batch_size=64, reuse=True)
        label_softmax = tf.nn.softmax(code_predLogit)
        myPrediction = tf.argmax(label_softmax, 1, name="predictions")

        totalN = np.shape(testX)[0]
        myN = int(totalN / self.batch_size)
        totalPredictions = []
        myCount = 0
        for i in range(myN):
            my1 = testX[self.batch_size * i:self.batch_size * (i + 1)]
            predictions = self.sess.run(myPrediction, feed_dict={self.inputs: my1})
            for k in range(self.batch_size):
                totalPredictions.append(predictions[k])

        totalPredictions = np.array(totalPredictions)
        totalPredictions = keras.utils.to_categorical(totalPredictions,4)

        return totalPredictions

    def predict(self):
        # define the classifier
        label_logits = Image_classifier(self.inputs, "Mini_classifier", reuse=True)
        label_softmax = tf.nn.softmax(label_logits)
        predictions = tf.argmax(label_softmax, 1, name="predictions")
        return predictions

    def Give_predictedLabels(self,testX):
        totalN = np.shape(testX)[0]
        myN = int(totalN / self.batch_size)
        myPrediction = self.predict()
        totalPredictions = []
        myCount = 0
        for i in range(myN):
            my1 = testX[self.batch_size * i:self.batch_size * (i + 1)]
            predictions = self.sess.run(myPrediction, feed_dict={self.inputs: my1})
            for k in range(self.batch_size):
                totalPredictions.append(predictions[k])

        totalPredictions = np.array(totalPredictions)
        totalPredictions = keras.utils.to_categorical(totalPredictions,10)
        return totalPredictions

    def Calculate_accuracy(self,testX,testY):
        #testX = self.mnist_test_x
        totalN = np.shape(testX)[0]
        myN = int(totalN / self.batch_size)
        myPrediction = self.predict()
        totalPredictions = []
        myCount = 0
        for i in range(myN):
            my1 = testX[self.batch_size * i:self.batch_size * (i + 1)]
            predictions = self.sess.run(myPrediction, feed_dict={self.inputs: my1})
            for k in range(self.batch_size):
                totalPredictions.append(predictions[k])

        totalPredictions = np.array(totalPredictions)

        testLabels = testY[0:np.shape(totalPredictions)[0]]
        testLabels = np.argmax(testLabels, 1)
        trueCount = 0
        for k in range(np.shape(testLabels)[0]):
            if testLabels[k] == totalPredictions[k]:
                trueCount = trueCount + 1

        accuracy = (float)(trueCount / np.shape(testLabels)[0])

        return accuracy

    def Calculate_Elbo(self,testX):
        # domain 1
        z_mean, z_log_sigma_sq = Encoder_SVHN(self.inputs, "encoder1", batch_size=64, reuse=True)

        continous_variables = z_mean + z_log_sigma_sq * tf.random_normal(tf.shape(z_mean), 0, 1, dtype=tf.float32)

        # define code classifier
        code_predLogit, code_pred = Code_Classifier(continous_variables, "code_classifier", 500, 10, 1, reuse=True)

        log_y = tf.log(code_pred + 1e-10)
        discrete_real = my_gumbel_softmax_sample(log_y, np.arange(self.len_discrete_code))

        code1 = tf.concat((continous_variables, discrete_real), axis=1)
        reco1 = Generator_SVHN("generator1", code1, reuse=True)
        reco2 = reco1

        y_labels = tf.argmax(discrete_real, 1)
        y_labels = tf.cast(y_labels, dtype=tf.float32)
        y_labels = tf.reshape(y_labels, (-1, 1))

        # VAE loss
        reconstruction_loss1 = tf.reduce_mean(tf.reduce_sum(tf.square(reco1 - self.inputs), [1, 2, 3]))

        KL_divergence1 = 0.5 * tf.reduce_sum(
            tf.square(z_mean - y_labels) + tf.square(z_log_sigma_sq) - tf.log(1e-8 + tf.square(z_log_sigma_sq)) - 1, 1)
        KL_divergence1 = tf.reduce_mean(KL_divergence1)

        vae_loss1 = reconstruction_loss1 + KL_divergence1

        myN = int(np.shape(testX)[0]/self.batch_size)
        sum = 0
        for i in range(myN):
            sum = sum + self.sess.run(vae_loss1,feed_dict={self.inputs:testX[i*self.batch_size:(i+1)*self.batch_size]})
        sum = sum / myN

        return sum

    def test(self):
        with tf.Session() as sess:
            self.saver = tf.train.Saver()

            self.sess = sess
            sess.run(tf.global_variables_initializer())
            self.saver.restore(sess, 'models/TeacherStudent_Supervised')

            batch_z = np.random.uniform(-1, 1, [self.batch_size, self.z_dim]).astype(np.float32)

            mnistElbo = self.Calculate_accuracy(self.mnist_test_x,self.mnist_label_test)
            svhnElbo = self.Calculate_accuracy(self.svhn_test_x,self.svhn_label_test)
            cifarElbo = self.Calculate_accuracy(self.cifar_test_x,self.cifar_test_label)

            avgElbo = mnistElbo + svhnElbo + cifarElbo
            avgElbo = avgElbo / 3.0

            print(mnistElbo)
            print('\n')
            print(svhnElbo)
            print('\n')
            print(cifarElbo)
            print('\n')
            print(avgElbo)
            print('\n')

    def Generate_GAN_Samples(self, n_samples, classN):
        myArr = []
        for tt in range(classN):
            y1 = np.zeros((self.batch_size, 4))
            y1[:, 0] = 1
            num1 = int(n_samples / self.batch_size)
            for i in range(num1):
                batch_z = np.random.uniform(-1, 1, [self.batch_size, self.z_dim]).astype(np.float32)

                g_outputs = self.sess.run(
                    self.GAN_output,
                    feed_dict={self.z: batch_z, self.y: y1})
                for t1 in range(self.batch_size):
                    myArr.append(g_outputs[t1])

        myArr = np.array(myArr)
        return myArr

    def train(self):

        isFirstStage = True
        with tf.Session() as sess:
            self.sess = sess
            sess.run(tf.global_variables_initializer())
            self.saver = tf.train.Saver()

            #self.saver.restore(sess, 'models/TeacherStudent_MNIST_TO_SVHN')

            # saver to save model
            self.saver = tf.train.Saver()
            taskCount = 3

            for taskIndex in range(taskCount):

                if taskIndex == 0:
                    dataX = self.mnist_train_x
                    dataY = self.mnist_train_y
                    labelY = self.mnist_label
                elif taskIndex == 1:
                    dataX = self.svhn_train_x
                    dataY = self.svhn_train_y
                    labelY = self.svhn_label
                elif taskIndex == 2:
                    dataX = self.cifar_train_x
                    dataY = self.CifarTrain_y
                    labelY = self.cifar_train_label

                if taskIndex > 0:
                    old_Nsamples = 60000
                    oldX = self.Generate_GAN_Samples(old_Nsamples, 1)
                    oldY = self.Make_DomainPredictions(oldX)
                    oldLabels = self.Give_predictedLabels(oldX)

                    oldX = oldX[0:np.shape(oldY)[0]]

                    # define combination of old and new datasets
                    # second state
                    dataX = np.concatenate((dataX, oldX), axis=0)
                    dataY = np.concatenate((dataY, oldY), axis=0)
                    labelY = np.concatenate((labelY,oldLabels),axis=0)

                counter = 0

                n_examples = np.shape(dataX)[0]

                start_epoch = 0
                start_batch_id = 0
                self.num_batches = int(n_examples / self.batch_size)

                mnistAccuracy_list = []
                mnistFashionAccuracy_list = []

                # loop for epoch
                start_time = time.time()
                for epoch in range(start_epoch, self.epoch):
                    count = 0
                    # Random shuffling
                    index = [i for i in range(n_examples)]
                    random.shuffle(index)
                    dataX = dataX[index]
                    dataY = dataY[index]
                    labelY = labelY[index]

                    # get batch data
                    for idx in range(start_batch_id, self.num_batches):
                        batch_images = dataX[idx * self.batch_size:(idx + 1) * self.batch_size]
                        batch_y = dataY[idx * self.batch_size:(idx + 1) * self.batch_size]
                        batch_labels = labelY[idx * self.batch_size:(idx + 1) * self.batch_size]

                        # update GAN
                        batch_z = np.random.uniform(-1, 1, [self.batch_size, self.z_dim]).astype(np.float32)

                        # update D network
                        _, d_loss = self.sess.run([self.d_optim, self.d_loss],
                                                  feed_dict={self.inputs: batch_images,self.gan_domain:batch_y,
                                                             self.z: batch_z, self.y: batch_y})

                        # update G and Q network
                        _, g_loss = self.sess.run(
                            [self.g_optim, self.g_loss],
                            feed_dict={self.inputs: batch_images, self.z: batch_z, self.y: batch_y})

                        #Train the domain classifier
                        _ = self.sess.run(self.domain_optim,feed_dict={self.inputs: batch_images, self.y: batch_y,self.z:batch_z,self.gan_domain:batch_y,self.labels:batch_labels})

                        #Train the classifier
                        _ = self.sess.run(self.classifier_optim,feed_dict={self.inputs: batch_images, self.y: batch_y,self.z:batch_z,self.gan_domain:batch_y,self.labels:batch_labels})

                        # update VAE
                        _, loss1 = self.sess.run([self.vae1_optim, self.vaeLoss],
                                                 feed_dict={self.inputs: batch_images, self.y: batch_y,self.z:batch_z,self.gan_domain:batch_y,self.labels:batch_labels})
                        class_loss = 0

                        outputs1, outputs2 = self.sess.run(
                            [self.output1, self.output2],
                            feed_dict={self.inputs: batch_images, self.y: batch_y,self.z:batch_z,self.gan_domain:batch_y})

                        g_outputs = self.sess.run(
                            self.GAN_output,
                            feed_dict={self.inputs: batch_images, self.z: batch_z, self.y: batch_y,self.gan_domain:batch_y})

                        # display training status
                        counter += 1
                        print("Epoch: [%2d] [%4d/%4d] time: %4.4f, d_loss: %.8f, g_loss: %.8f, vae_loss:%.8f. c_loss:%.8f" \
                              % (epoch, idx, self.num_batches, time.time() - start_time, d_loss, g_loss, loss1, 0))

                    y_RPR1 = np.reshape(outputs1, (-1, 32, 32,3))
                    g_output = np.reshape(g_outputs, (-1, 32, 32,3))
                    ims("results/" + "MNIST" + str(epoch) + ".png", merge2(y_RPR1[:64], [8, 8]))
                    ims("results/" + "GAN" + str(epoch) + ".png", merge2(g_output[:64], [8, 8]))

                '''
                lossArr1 = np.array(mnistAccuracy_list).astype('str')
                f = open(myThirdName, "w", encoding="utf-8")
                for i in range(np.shape(lossArr1)[0]):
                    f.writelines(lossArr1[i])
                    f.writelines('\n')
                f.flush()
                f.close()

                lossArr1 = np.array(mnistFashionAccuracy_list).astype('str')
                f = open("results/MnistToSVHN_svhnAccuracy.txt", "w", encoding="utf-8")
                for i in range(np.shape(lossArr1)[0]):
                    f.writelines(lossArr1[i])
                    f.writelines('\n')
                f.flush()
                f.close()
                '''
                self.saver.save(self.sess, "models/TeacherStudent_Supervised")

infoMultiGAN = LifeLone_MNIST()
infoMultiGAN.build_model()
infoMultiGAN.train()
#infoMultiGAN.train_classifier()
infoMultiGAN.test()
