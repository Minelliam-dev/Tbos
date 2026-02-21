def main():
    writing = True
    text_content = ""
    while writing == True:
        text_input = input("")
        if text_input == "[exit]":
            writing = False
        if writing:
            text_content += text_input
    return text_content
