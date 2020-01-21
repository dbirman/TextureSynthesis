import numpy as np
import tensorflow as tf
import os
import sys, time
import argparse

from SpatialTextureSynthesis import *
from model import *
from skimage.io import imread, imsave
from skimage.transform import resize
import pickle


def main(args):
    # Keep track of how long this all takes.
    start_time = time.time()

    weights_file = 'vgg19_normalized.pkl'

    # Load VGG-19 weights and build model.
    with open(weights_file, 'rb') as f:
        vgg_weights = pickle.load(f)['param values']
    vgg19 = VGG19(vgg_weights)
    vgg19.build_model()

    # Weights to determine how much each layer will factor into the loss function.
    style_layers = ['conv1_1', 'pool1', 'pool2', 'pool3', 'pool4', 'pool5']
    if args.layer not in style_layers:
        print('Error! Your requested style layer must be one of {}'.format(style_layers))
        return
    this_layer_weight = {style_layers[i]: 1e9 for i in range(style_layers.index(args.layer))}

    # Load up original image
    image_path = '{}/{}.jpg'.format(args.inputdir, args.image)
    original_image = preprocess_im(image_path)
    #print(original_image.shape)

    # Load up guides
    guide_dir = '/Users/akshay/proj/TextureSynthesis/tensorflow_synthesis/Receptive_Fields/MetaWindows_clean_s0.3'
    nGuides = len(os.listdir(guide_dir))
    nGuides=10
    guides = np.zeros((original_image.shape[1], original_image.shape[2], nGuides))
    for i, imName in enumerate(os.listdir(guide_dir)[:nGuides]):
        guideI = resize(imread('{}/{}'.format(guide_dir, imName)), (original_image.shape[1], original_image.shape[2]))
        guides[:,:,i] = guideI

    print(guideI.shape, guides.shape)
    print('Synthesizing texture {} matching up through layer {} for {} iterations'.format(args.image, args.layer, args.iterations))
    
    # Make a temporary directory to store outputs
    tmpDir = "%s/iters" % (args.outputdir)
    os.system("mkdir -p %s" %(tmpDir))    

    # Initialize texture synthesis
    args.saveName = 'test'
    saveParams = {'saveDir': args.outputdir, 'saveName': args.saveName}
    text_synth = SpatialTextureSynthesis(vgg19, original_image, guides, this_layer_weight, saveParams, iterations=args.iterations+1)

    # Do training
    if args.generateMultiple==1:
        for i in range(args.sampleidx):
            print('Generating sample {} of {}'.format(i+1, args.sampleidx))
            text_synth.train(i+1)
    else:
        text_synth.train(args.sampleidx) 
    postprocess_img(tmpDir, args)

    print('DONE. This took {} seconds'.format(time.time()-start_time))
    sys.stdout.flush()

def preprocess_im(path):
    MEAN_VALUES = np.array([123.68, 116.779, 103.939]).reshape((1,1,1,3))
    image = imread(path)

    if image.shape[1]!=256 or image.shape[0]!=256:
        image = resize(image, (256,256))

    # Resize the image for convnet input, there is no change but just
    # add an extra dimension.
    image = np.reshape(image, ((1,) + image.shape))
    if len(image.shape)<4:
        image = np.stack((image,image,image),axis=3)

    # If there is a Alpha channel, just scrap it
    if image.shape[3] == 4:
        image = image[:,:,:,:3]

    # Input to the VGG model expects the mean to be subtracted.
    image = image - MEAN_VALUES
    return image


def postprocess_img(raw, args):
    for im in os.listdir(raw):
        if 'step_{}.npy'.format(args.iterations) in im and '{}x{}_{}_{}'.format(args.nPools, args.nPools, args.layer, args.image) in im:
            imName = raw+'/'+im
            imi = np.load(imName)
            outName = '{}/{}'.format(args.outputdir, im[:im.index('_step')])

            # Save as PNG into outdir
            imsave(outName + '.png', imi)

            # Also copy .npy fileinto outdir
            os.system('cp %s %s.npy' % (imName, outName))
            print('{} saved as PNG to {}'.format(im, args.outputdir))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--layer", default="pool2")
    parser.add_argument("-d", "--inputdir", default="/Users/akshay/proj/TextureSynthesis/stimuli/textures/orig_all")
    parser.add_argument("-o", "--outputdir", default="/Users/akshay/proj/TextureSynthesis/stimuli/textures/test")
    parser.add_argument("-i", "--image", default="rocks")
    parser.add_argument("-s", "--sampleidx", type=int, default=1)
    parser.add_argument("-p", "--nPools", type=int, default=1)
    parser.add_argument('-g', '--generateMultiple',type=int, default=0)
    parser.add_argument('-n', '--iterations', type=int, default=10000)
    args = parser.parse_args()
    main(args)
    #tmpDir = "%s/iters" % (args.outputdir)
    #postprocess_img(tmpDir, args)
 
