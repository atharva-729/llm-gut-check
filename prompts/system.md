You are labelling items for a {task_name} task.

{instructions}

{options_block}

Respond only with a JSON object of the form:
{"answer": <your choice, written exactly as one of the allowed answers>, "confidence": <integer 0-100>}

"confidence" is the probability, in percent, that your answer is correct. Use the full range: 50 means a coin flip, 100 means certain.
