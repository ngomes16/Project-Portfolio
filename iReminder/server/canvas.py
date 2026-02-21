#14559~csUpUMVrtfZkE1HAUrpgkBzgEUglg1ebr9AXeyJISTHH6rn3wKbjYBZhXYQn7xhD

# from syslog import closelog
import requests


def get_courses(token):
    base_url = "https://canvas.instructure.com/api/v1/"
    url = base_url+"courses?access_token="+token
    canvas_all = requests.get(url).json()
    course_names_urls = []
    user_id = ""

    for course in canvas_all:
        if ('access_restricted_by_date' in course and course['access_restricted_by_date']):
            continue
        if user_id == "":
            user_id = course['enrollments'][0].get('user_id')
    
        base_url = "https://canvas.instructure.com/api/v1/users/"
        url = base_url+str(user_id)+"/courses/"+str(course['id']) + "/assignments?access_token=" + token
     #   print(url)
        course_names_urls.append((course['name'], url))
    return course_names_urls


# AI-generated
def parse_assignment(assignment, course_name, platform="canvas", time_zone="CDT"):
    due_date = "N/A"
    due_time = "N/A"
    if (assignment['due_at']):
        due_date = assignment['due_at'][5:7] + "/" + assignment['due_at'][8:10] + "/" +assignment['due_at'][0:4]
        due_time = assignment['due_at'][11:19]
    else:
        time_zone = "N/A"
    return {
        "CourseName" : course_name,
        "AssignmentName" : assignment['name'],
        "DueDate" : due_date,
        "DueTime" : due_time,
        "TimeZone" : time_zone,
        "Platform" : platform  
    }

def get_assignments(api_token):
    # print(token)
    course_names_urls = get_courses(api_token)    
    all_assignments = []
    i = 0
    for i in range(len(course_names_urls)):
        assignment_list = requests.get(course_names_urls[i][1]).json()
        for assignment in assignment_list:
            # print(assignment)
            # print(course_names[i])
            all_assignments.append(parse_assignment(assignment, course_names_urls[i][0]))
    # print(all_assignments)
    return all_assignments

# get_assignments("14559~KgbYlf8d9JUAPV5MJP6NiQpdShuIGyQNzkKtiR5QWlfVOxcWqIRdxttT8bgODWlT")

# get_courses("14559~KgbYlf8d9JUAPV5MJP6NiQpdShuIGyQNzkKtiR5QWlfVOxcWqIRdxttT8bgODWlT")