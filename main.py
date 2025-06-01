from runner.frotz_runner import FrotzRunner

def main():
    runner = FrotzRunner('games/905.z5')
    output = runner.run_commands(['look', 'inventory'])
    print(output)

if __name__ == '__main__':
    main()
