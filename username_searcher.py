from openai import OpenAI

class UsernameSearch:
    def __init__(self, openai_timeout = 360):
        self.base_instruction = """
        # Purpose
        Your task is to identify the real name corresponding to a given LessWrong username.

        # Instructions
        Begin with a concise checklist (3-7 bullets) of your approach to matching the username to a real name.
        - Use only the information provided from the LessWrong API to conduct your research.
        - The goal is to match the username to a real name suitable for searches on Google Scholar and other academic platforms.
        - If the user info is not enough, try to perform searches with the nickname in lesswrong and the web to try to find it.
        - If a username does not appear to have academic works or a reliable real name match, explicitly acknowledge this.
        - Always indicate when no match is found, or if no real name is available; do not speculate or reveal unverifiable identities.
        After each attempt, validate your result in 1-2 lines and clarify whether the name found meets the criteria for academic search.

        # Output
        - Clearly specify the real name if found.
        - If no real name is discovered, explicitly state that it was not possible to determine or match the username.
        """

        # This dict should store like a history for username searches
        self.searches = {}

        #self.last_response = None
        self.last_search_id = None
        self.last_search_response = None
        self.last_search_status = None

        self.client = OpenAI(timeout = openai_timeout)

    def start_user_search(self, user_info:str):
        '''
        Recieves a json representing the user informantion from the lesswrong forum and starts a deep research
        process with the o4-mini-deep-research model.
        
        Not implemented yet:
            - Store the query info as part of the searches history
        '''

        response = self.client.responses.create(
            model="o4-mini-deep-research",
            input= user_info,
            instructions= self.base_instruction,
            background=True,
            tools=[
                {"type": "web_search_preview"}
            ],
        )
        
        self.last_search_id = response.id
        self.last_search_status = response.status
        self.last_search_response = response.output_text

        print(f'starting search for user {user_info}, queued with id = {self.last_search_id}')

    def show_last_search_response(self):
        '''
        Retrieves the last response output text if available. It also updates the 'last_responses'
        var informantion and tells you if the process has not finished yet.
        '''

        retrieved_response = self.client.responses.retrieve(self.last_search_id)

        self.last_search_status = retrieved_response.status
        self.last_search_response = retrieved_response.output_text

        if retrieved_response.status != 'completed':
            
            return f'job id = {self.last_search_id} not completed, status is {self.last_search_status}'
        
        return retrieved_response.output_text

    def list_search_history(self):
        '''
        This should use the dict from self.searches to list all queued, started, and finished searches
        '''
        pass

    def get_response(self, id:str):
        '''
        Recieves the response id of a backgrounded task and returns the response. If it has not finished,
        it tells the user the current status.
        '''
        try:
            retrieved_response = self.client.responses.retrieve(id)

            if retrieved_response.status != 'completed':
                
                return f'job id = {retrieved_response.id} not completed, status is {retrieved_response.status}'
            
            return retrieved_response.output_text

        except Exception as e:
            
            return f'error: {e}'
    
    def get_status(self, id:str):
        '''
        Retrieves the current response status given the response id
        '''
        
        try:
            retrieved_response = self.client.responses.retrieve(id)

            return retrieved_response.status

        except Exception as e:
            print(f'error: {e}')
            return 'error'

    def set_instruction(self, instruction:str):
        pass

    def show_instruction(self):
        pass