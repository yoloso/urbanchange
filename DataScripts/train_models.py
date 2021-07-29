from subprocess import check_call
import sys


PYTHON = sys.executable

COMMANDS = [
    'python train.py --batch 4 --cfg models/yolov5s.yaml --weights yolov5s.pt --img 640 --hyp data/hyps/hyp.modified.yaml --epochs 100 --data data.yaml --name freeze_lr0001 --project urbanchange --device 0 --entity urbanchange',
    'python train.py --batch 4 --cfg models/yolov5s.yaml --weights yolov5s.pt --img 640 --hyp data/hyps/hyp.modified2.yaml --epochs 100 --data data.yaml --name freeze_lr0005 --project urbanchange --device 0 --entity urbanchange']


if __name__ == '__main__':
    # Loop over each command
    for i, cmd in enumerate(COMMANDS):
        print('[INFO] Running command #{}'.format(i))

        # Execute
        print(cmd)
        check_call(cmd, shell=True)

print('[INFO] Complete.')
