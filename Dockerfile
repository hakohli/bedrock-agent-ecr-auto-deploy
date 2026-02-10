FROM public.ecr.aws/lambda/python:3.12

COPY tool_executor.py ${LAMBDA_TASK_ROOT}/

CMD ["tool_executor.lambda_handler"]
