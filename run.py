from arya import create_app

if __name__ == '__main__':
    app = create_app(demo=False, test=True)
    app.run(debug=True, host='0.0.0.0')
    
