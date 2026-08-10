#!/usr/bin/env python

def main(**kwargs):
    print("fuck the world")
    from .common import main
    main(**kwargs)


if __name__ == '__main__':
    main()
