from data.color import munroecorpus
from ref import RefTask

import cairo
import colorsys
from collections import defaultdict
import numpy as np
import os

MIN_COUNT = 5
EXCLUDED = ["shit", "very"]

VAL_FRAC = 0.1
TEST_FRAC = 0.1

class ColorRefTask(RefTask):
    def __init__(self):
        n_features = 3
        super(ColorRefTask, self).__init__(n_features)
        train_corpus = munroecorpus.get_training_handles()
        val_corpus = munroecorpus.get_dev_handles()
        test_corpus = munroecorpus.get_test_handles()
        self.vocab = {"_": 0, "UNK": 1}
        self.reverse_vocab = {0: "_", 1: "UNK"}
        self.colors = {
            "train": [],
            "val": [],
            "test": []
        }
        self.names = {
            "train": [],
            "val": [],
            "test": []
        }
        self.reps = {
            "train": [],
            "val": [],
            "test": []
        }
        self.randoms = {
            "train": np.random.RandomState(0),
            "val": np.random.RandomState(0),
            "test": np.random.RandomState(0)
        }

        word_counts = defaultdict(lambda: 0)
        for name in train_corpus[0]:
            name = name.replace("-", " ")
            for word in name.split(" "):
                word_counts[word] += 1
        common_words = [w for w, c in word_counts.items() if c >= MIN_COUNT and
                w not in EXCLUDED]

        for word in common_words:
            index = len(self.vocab)
            self.vocab[word] = index
            self.reverse_vocab[index] = word
        self.lexicon = [[0]] + [[i] for i in range(2, len(self.vocab))]
        self.empty_desc = np.zeros(len(self.lexicon))
        self.empty_desc[0] = 1

        for name in train_corpus[0]:
            words = name.replace("-", " ").split(" ")
            rep = np.zeros(len(self.lexicon))
            out = []
            for i_l, l in enumerate(self.lexicon):
                if all(self.reverse_vocab[w] in words for w in l):
                    rep[i_l] = 1
                    out += l
            if len(out) == 0:
                continue
            assert rep.any()
            rep /= np.sum(rep)

            files = [c[name] for c in train_corpus]
            colors = np.array([munroecorpus.open_datafile(f) for f in files]).T
            to_val = int(len(colors) * (1 - VAL_FRAC - TEST_FRAC))
            to_test = int(len(colors) * (1 - TEST_FRAC))
            train_colors = colors[:to_val].copy()
            val_colors = colors[to_val:to_test].copy()
            test_colors = colors[to_test:].copy()
            for color in train_colors:
                self.colors["train"].append(color)
                self.names["train"].append(out)
                self.reps["train"].append(rep)
            for color in val_colors:
                self.colors["val"].append(color)
                self.names["val"].append(out)
                self.reps["val"].append(rep)
            for color in test_colors:
                self.colors["test"].append(color)
                self.names["test"].append(out)
                self.reps["test"].append(rep)

        for fold in ("train", "val", "test"):
            self.colors[fold] = np.asarray(self.colors[fold])
            self.colors[fold][:, 0] /= 360.
            self.colors[fold][:, 1:] /= 100.
            assert np.max(self.colors[fold]) <= 1

        self.image_counter = 0

    def reset_test(self):
        self.randoms["val"] = np.random.RandomState(0)
        self.randoms["test"] = np.random.RandomState(0)

    def get_pair(self, fold):
        colors = self.colors[fold]
        reps = self.reps[fold]
        i1, i2 = self.randoms[fold].randint(colors.shape[0], size=2)
        rep = reps[i1]
        return colors[i1, :], colors[i2, :], rep, None, None

    def visualize(self, state, agent):
        r1, g1, b1 = colorsys.hsv_to_rgb(*state.left)
        r1 = int(100 * r1)
        g1 = int(100 * g1)
        b1 = int(100 * b1)

        r2, g2, b2 = colorsys.hsv_to_rgb(*state.right)
        r2 = int(100 * r2)
        g2 = int(100 * g2)
        b2 = int(100 * b2)

        block1 = "<span style='display: inline-block; width: 20px; height: 20px; background: rgb(%s%%, %s%%, %s%%); border: 2px solid #000'></span>" % (r1, g1, b1)
        block2 = "<span style='display: inline-block; width: 20px; height: 20px; background: rgb(%s%%, %s%%, %s%%); border: 2px solid #000'></span>" % (r2, g2, b2)
        if agent == 0 and state.target == 1:
            block1, block2 = block2, block1
        #return block1 + " " + block2
        return block1

    def turk_visualize(self, state, agent, loc):
        data1 = np.zeros((200, 200, 4), dtype=np.uint8)
        surf1 = cairo.ImageSurface.create_for_data(data1, cairo.FORMAT_ARGB32, 200, 200)
        ctx1 = cairo.Context(surf1)
        rgb1 = colorsys.hsv_to_rgb(state.left[0], state.left[1], state.left[2])
        ctx1.set_source_rgb(*rgb1)
        ctx1.paint()
        ctx1.fill()

        data2 = np.zeros((200, 200, 4), dtype=np.uint8)
        surf2 = cairo.ImageSurface.create_for_data(data2, cairo.FORMAT_ARGB32, 200, 200)
        ctx2 = cairo.Context(surf2)
        rgb2 = colorsys.hsv_to_rgb(state.right[0], state.right[1], state.right[2])
        ctx2.set_source_rgb(*rgb2)
        ctx2.paint()
        ctx2.fill()

        if agent == 0 and state.target == 1:
            surf1, surf2 = surf2, surf1

        name1 = "%d_a.png" % self.image_counter
        name2 = "%d_b.png" % self.image_counter

        surf1.write_to_png(os.path.join(loc, name1))
        surf2.write_to_png(os.path.join(loc, name2))
        self.image_counter += 1

        return name1, name2

    def pp(self, indices):
        return " ".join([self.reverse_vocab[i] for i in indices])
